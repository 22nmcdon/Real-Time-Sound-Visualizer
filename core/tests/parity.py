"""The C++ core against the page's JavaScript, sample for sample.

The core is a port of code that already works and is already tested
(web/tests), so the test that matters is not whether the C++ is reasonable
but whether it is the SAME: the same scenario through `makeEnvelope`, read
out of web/scope.html itself, and through scope::Envelope, compared a sample
at a time. A copy of the JavaScript kept here would be a second thing to
drift, so the runner lifts the function from the page by name.

Held to 1e-12 rather than to equality. The two agree on every operation's
order, but `Math.exp` and `Math.log` are V8's and `std::exp` and `std::log`
are the C library's, and the two are allowed to differ in the last place.

Null tests, as the web suite has them: the same comparison against the page's
values shifted by one sample, and against a run with one tone value changed,
must both fail - a comparison that could not tell those apart would pass
whatever the port did.
"""
import os, subprocess, sys, glob, math

HERE = os.path.dirname(os.path.abspath(__file__))
CORE = os.path.dirname(HERE)
BUILD = os.path.join(CORE, "build", "parity")
TOL = 1e-12

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

def build(tool):
    os.makedirs(BUILD, exist_ok=True)
    exe = os.path.join(BUILD, tool)
    src = os.path.join(HERE, "tools", tool + ".cpp")
    subprocess.run(["g++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror", "-I", os.path.join(CORE, "include"),
                    src, "-o", exe], check=True)
    return exe

def values(cmd):
    out = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.split()
    return [float(v) for v in out]

def _one(call):
    path = os.path.join(BUILD, "one.txt")
    with open(path, "w") as f: f.write(call + "\n")
    return path

# NaN on one side and a number on the other is as far apart as two values can
# be. It used to count as no difference at all - `max` never takes a NaN after
# a number - which is how a run the page answered with NaN, and the core with
# memory read past the end of a vector, passed as the same to 1e-12.
def worst(a, b):
    if len(a) != len(b): return float("inf")
    return max((0.0 if x == y or (math.isnan(x) and math.isnan(y)) else
                float("inf") if math.isnan(x) or math.isnan(y) else abs(x - y) for x, y in zip(a, b)), default=0.0)
nan, inf = float("nan"), float("inf")
check("the comparison sees a NaN against a number, after a number and before one",
      worst([1, nan], [1, 2]) == inf and worst([1, 2], [1, nan]) == inf and worst([nan, 1], [2, 1]) == inf)
check("and NaN against NaN, or an infinity against itself, as the same",
      worst([nan, inf, -inf], [nan, inf, -inf]) == 0 and worst([inf], [-inf]) == inf)

print("\n--- the envelope ---")
exe = build("envelope_cpp")
scenarios = sorted(glob.glob(os.path.join(HERE, "scenarios", "envelope_*.txt")))
for path in scenarios:
    name = os.path.basename(path)[len("envelope_"):-4]
    js = values(["node", os.path.join(HERE, "tools", "envelope_js.mjs"), path])
    cpp = values([exe, path])
    # A scenario that never moves proves nothing about the stages.
    moved = max(js) - min(js) if js else 0
    check("%s: %d samples, the same to %g" % (name, len(js), TOL), worst(js, cpp) <= TOL and moved > 0.5,
          "worst %.3g, range %.3f" % (worst(js, cpp), moved))

print("\n--- the nulls ---")
path = os.path.join(HERE, "scenarios", "envelope_adsr.txt")
js = values(["node", os.path.join(HERE, "tools", "envelope_js.mjs"), path])
cpp = values([exe, path])
shifted = js[1:] + js[-1:]
check("the comparison fails against the page's values a sample late", worst(shifted, cpp) > 1e-6,
      "worst %.3g" % worst(shifted, cpp))
altered = os.path.join(BUILD, "adsr_altered.txt")
with open(path) as f, open(altered, "w") as g:
    g.write(f.read().replace("tone releaseMs 150", "tone releaseMs 151"))
check("and against a release a millisecond longer", worst(values([exe, altered]), js) > 1e-6,
      "worst %.3g" % worst(values([exe, altered]), js))

print("\n--- the waveforms and the functions under them ---")
import random, math
rng = random.Random(20261001)   # fixed, so a failure is the same failure next time
TWO_PI = 2 * math.pi

def calls():
    """Every call, weighted towards where a port goes wrong: a phase exactly on
    a cycle's corner and a hair either side, negative phases and phases far
    past one cycle, a blep window at its edges, widths and positions out of
    range, and names the page does not know."""
    out = []
    corners = [k / 4 for k in range(5)] + [0.3, 0.05, 0.95]
    eps = [0, 1e-12, -1e-12, 1e-6, -1e-6]
    phases = [TWO_PI * (c + e) + TWO_PI * n for c in corners for e in eps for n in (-3, 0, 1, 7)]
    phases += [rng.uniform(-40, 60) for _ in range(120)] + [1e6, -1e6, 0.0]
    for p in phases: out.append("cycleOf %r" % p)
    for dt in (0, -0.1, 0.001, 0.01, 0.1, 0.49):
        for t in [0, 1e-9, dt / 2, dt, dt * 1.0001, 0.5, 1 - dt, 1 - dt / 2, 1 - 1e-9] + [rng.random() for _ in range(10)]:
            out.append("polyBlep %r %r" % (t, dt)); out.append("polyBlamp %r %r" % (t, dt))
    for level in (-1, 0, 1e-9, 0.5, 0.999, 1, 3.7, 7.99, 8, 9):
        out.append("drawbarGain %r" % level)
    for _ in range(40):
        out.append("drawbarWeights " + ",".join("%r" % rng.choice([0, 0, 1, 3, 5, 8, rng.uniform(0, 8)]) for _ in range(9)))
    out.append("drawbarWeights 0,0,0,0,0,0,0,0,0")
    for i in range(13):
        for just in (0, 1): out.append("intervalRatio %d %d" % (i, just))
    for rate in (44100.0, 48000.0, 96000.0):
        for fc in (20, 440.5, 1000, 0.3 * rate, 0.49 * rate, 0.6 * rate):
            out.append("svfG %r %r" % (fc, rate))
    for _ in range(30):
        g = math.tan(math.pi * rng.uniform(20, 20000) / 48000)
        x = ",".join("%r" % rng.uniform(-1, 1) for _ in range(64))
        out.append("svfRun %r %r %d %s" % (g, rng.choice([2, 1.414, 0.5, 0.1]), rng.randint(0, 4), x))
    # Drawn cycles: tables of 16, 8, 4, 2 points, every value a multiple of a
    # sixty-fourth so it is a float exactly, as a Float32Array would hold it.
    def table_set():
        sizes = [16, 8, 4, 2]
        return "%d:%s" % (sizes[0] // 2, ";".join(",".join("%r" % (rng.randint(-64, 64) / 64) for _ in range(n)) for n in sizes))
    cycles = [table_set() for _ in range(4)]
    for c in cycles:
        for p in phases[::9]:
            for step in (0, 1e-4, 0.01, 0.1, 0.3):
                out.append("cycleRead T:%s %r %r" % (c, p, step))
    shapes = ["sine", "triangle", "square", "ramp", "pulse", "morph", "drawbars", "harmonic", "nonsense"]
    amounts = {"pulse": [0, 0.05, 0.3, 0.5, 0.97, -1], "morph": [0, 0.5, 1, 1.7, 2, 2.5, 3, 3.5, -1]}
    weights = ",".join("%r" % w for w in (0.1, 0, 0.3, 0.2, 0, 0.05, 0, 0, 0.35))
    # The drawbars fade each partial out over the last twentieth of a cycle a
    # sample, so their steps put each of the nine inside that band: with the
    # steps the other shapes use, every partial was either wholly in or
    # wholly out, and a band twice as wide passed.
    fade_steps = sorted({0.47 / m for m in (0.5, 1.5, 1, 2, 3, 4, 5, 6, 8)})
    for shape in shapes:
        for p in phases[::3]:
            for step in (0, 0.001, 0.02, 0.2, 0.6) + (tuple(fade_steps) if shape == "drawbars" else ()):
                for amount in amounts.get(shape, [0]):
                    bars = weights if (shape == "drawbars" and rng.random() < 0.5) else "-"
                    out.append("waveAt %s %r %r %s %r" % (shape, p, step, bars, amount))
    for p in phases[::5]:
        for step in (0, 0.01, 0.2):
            out.append("waveAt drawn %r %r T:%s 0" % (p, step, cycles[0]))
            for amount in (0, 0.4, 1, 2.9, 3, 5):
                out.append("waveAt wavetable %r %r B:%s %r" % (p, step, "!".join(cycles), amount))
    # The noises: each shape from a few seeds, at a low note and a high one,
    # so the stepped noise both holds for many samples and steps every few.
    for shape in ("noise", "pink", "brown", "stepped"):
        for seed in (1, 7, 123456):
            for hz in (55.0, 1760.0):
                out.append("noiseRun %s %d 600 %r 48000" % (shape, seed, hz))
    # And a note standing still: the stepped noise steps when its phase goes
    # back, and only a phase that does not move can tell "back" from "not on".
    out.append("noiseRun stepped 3 100 0.0 48000")
    # The oscillator: every shape against each of its features alone and all
    # of them together, with the pitch gliding and unison changing part-way,
    # which is the restart path. A sync ratio that sweeps puts the reset at
    # every fraction of a sample; a whole one puts it at the slave's wrap.
    features = [
        dict(),
        dict(n=3, cents=15),
        dict(n=7, cents=40, n2=2),
        # Half a copy: the page's Math.round takes 2.5 to three, C++'s round
        # would too, but floor would take it to two - and a count of three
        # copies is not the sound of two.
        dict(n=2.5, cents=10, n2=4.5),
        dict(fm=2.5, mod=1.5),
        dict(fm=0.7, mod=0.5, fmr=1),
        dict(ring=0.6, mod=3),
        dict(sync=2, syncr=1),
        dict(sync=1.37, sweep=1.9),
        dict(sub=0.8, suboct=2),
        dict(sub=0.4, subsine=1),
        dict(n=5, cents=20, fm=1.2, mod=2, ring=0.3, sync=1.5, sweep=0.7, sub=0.5, suboct=2, offset=0.4),
    ]
    for shape in ("sine", "triangle", "square", "ramp", "pulse", "morph", "drawbars", "harmonic"):
        for f in features:
            p = dict(shape=shape, rate=48000.0, hz=110.0, hz2=rng.choice([110.0, 330.0, 2600.0]), n=1, n2=1, flip=-1,
                     cents=0, fm=0, mod=1, ring=0, sync=1, sweep=0, sub=0, suboct=1, subsine=0, offset=0,
                     amount=rng.choice([0, 0.3, 1.6, 2.5]), samples=700, fmr=0, syncr=0, bars="-")
            p.update(f)
            if "n2" in f or "n" in f: p["flip"] = 350; p.setdefault("n2", p["n"])
            if shape == "drawbars" and rng.random() < 0.5: p["bars"] = weights
            out.append("oscRun " + " ".join("%s=%s" % (k, v if isinstance(v, str) else repr(v)) for k, v in p.items()))
    # The voice after its oscillator. The shaper at both factors, from nothing
    # to all of both, with pushes past each end of their range and a fold
    # small enough to be normalised (under a quarter turn); a signal that
    # swings past one, so the drive's knee and the fold's turns are reached.
    for factor in (2, 4):
        out.append("lowpassTaps %d" % factor)
        # 0.12 is a fold between a quarter and a half turn, the one range where
        # normalising "under a quarter turn" and "under a half" disagree.
        for drive, fold, dp, fpush in ((0, 0, 0, 0), (0.5, 0, 0, 0), (0, 0.05, 0, 0), (0, 0.12, 0, 0), (0, 0.6, 0, 0), (1, 1, 0, 0),
                                       (0.3, 0.2, 0.9, -0.5), (0.7, 0.8, -1, 0.4)):
            xs = ",".join("%r" % (1.3 * math.sin(i * 0.21) + 0.2 * rng.uniform(-1, 1)) for i in range(160))
            out.append("shapeRun %d %r %r %r %r %s" % (factor, drive, fold, dp, fpush, xs))
    # The crush, with values on exact halves of its steps - where JavaScript's
    # rounding and C++'s differ - and a hold faster and slower than the rate.
    for hz in (0, 900.0, 11025.0, 60000.0):
        for bits in (0, 1, 4, 8):
            q = 2 ** (bits - 1) if bits else 1
            # And the double just under a half, which floor(x + 0.5) rounds up
            # and Math.round does not.
            halves = [(k + 0.5) / q for k in range(-3, 3)] + [0.49999999999999994 / q]
            xs = ",".join("%r" % v for v in halves + [rng.uniform(-1, 1) for _ in range(40)])
            out.append("crushRun %r %r 48000 %s" % (hz, bits, xs))
    # The filter, with an envelope that holds and moves - its coefficient is
    # worked out again only when something it depends on has moved - and
    # cutoffs past the clamp at both ends.
    for cutoff in (5.0, 800.0, 30000.0):
        for env_amt, track, note in ((0, 0, 0.0), (2.0, 0.5, 110.0), (-1.5, 1, 880.0)):
            for q, kind in ((0.05, 1), (0.7071, 2), (4.0, 3), (1.0, 4)):
                xs = ",".join("%r" % rng.uniform(-1, 1) for _ in range(96))
                envs = ",".join("%r" % (0.0 if i < 10 else min(1.0, (i - 10) / 30) if i < 60 else 0.6) for i in range(96))
                # And one of the tone's three filter settings moved part-way,
                # while the envelope and the push hold still - so the moved
                # setting is the only thing that can ask for a new coefficient.
                field = rng.choice(["cutoff", "env", "track"])
                moved = {"cutoff": cutoff * 1.7, "env": env_amt + 0.8, "track": track + 0.5}[field]
                out.append("vcfRun %r %r %r %r %d %r 48000 %r %s %s %s %r" % (cutoff, env_amt, track, q, kind, note,
                                                                             rng.choice([0, 0.7]), xs, envs, field, moved))
    out += [voices_call(v) for v in voice_scenarios()]
    out += [plane_call(v) for v in plane_scenarios()]
    out += drawing_calls()
    return out

SOLIDS = ["Cube", "Tetrahedron", "Octahedron", "Dodecahedron", "Icosahedron", "Torus", "Knot"]

def drawing_calls():
    """The figures at their corners and between, each detail rounded either
    way and fractional where the figure keeps the fraction, a rose far into
    its turns; a compiled path, a path of one point and none. The solids as
    built, and walked: turned, slow and fast, switched and reset mid-lap.
    The LFOs, the random one fast enough to draw many times."""
    out = []
    figures = ["Circle", "Square", "Polygon", "Star", "Rose", "Heart", "Infinity", "Spiral", "Spirograph",
               "Butterfly", "Nonsense"]
    ts = sorted({k / d for d in (4, 5, 6, 7, 8, 12) for k in range(d)} | {rng.random() for _ in range(12)}
                | {0.999999999, 1e-12})
    for name in figures:
        for detail in (0, 2.5, 3, 4.5, 5, 6.5, 7, 12):
            for t in ts:
                out.append("figureAt %s %r %r -" % (name, t, detail))
    for t in (0.0, 1.25, 517.3, 10079.999):
        out.append("figureAt Rose %r 3.7 -" % t)
    path = "P:-0.5,0.2,0.3,0.8,0.9,-0.4,-0.1,-0.7,0.4,0.1,-0.5,0.2;0,0.18,0.5,0.5,0.86,1"
    for t in ts + [3.4, 0.5, 0.18]:
        for name in ("Text", "Path", "Drawn"):
            out.append("figureAt %s %r 5 %s" % (name, t, path))
    # A path with a time more than it has points, which the path above was by
    # mistake for as long as this harness has had it. The page reads the
    # missing point as undefined and answers NaN past the last one; the core
    # read past the end of its vector, and the comparison skipped NaN, so
    # both went unseen. Nothing the page builds is short; this holds the core
    # to NaN rather than to whatever memory follows.
    short = "P:-0.5,0.2,0.3,0.8,0.9,-0.4,-0.1,-0.7,-0.5,0.2;0,0.18,0.5,0.5,0.86,1"
    for t in (0.1, 0.6, 0.9, 0.99):
        out.append("figureAt Path %r 5 %s" % (t, short))
    out.append("figureAt Drawn 0.3 5 P:0.4,0.4;0")
    out.append("figureAt Text 0.3 5 -")
    for s in SOLIDS: out.append("solidData " + s)
    # Math.hypot to the last bit: V8 scales by the largest and compensates the
    # sum, which only the last place shows. Values whose squares carry well
    # past a double's width, so the compensation has something to keep.
    for _ in range(400):
        vals = [rng.uniform(-1, 1) * 10 ** rng.randint(-3, 3) for _ in range(rng.choice([2, 3]))]
        out.append("hypot " + " ".join("%r" % v for v in vals))
    out.append("hypot 0.0 0.0 0.0")
    for s in SOLIDS:
        out.append("wireRun model=%s samples=1800 rate=48000 laps=40 depth=0.45 s0=0.11 s1=0.17 s2=0.3 ev=" % s)
    out.append("wireRun model=Cube samples=3000 rate=48000 laps=300 depth=0.9 s0=2 s1=-1.3 s2=0.7 "
               "ev=700:model:Knot;1300:depth:0.1;1900:reset;2300:model:Torus;2600:model:Torus")
    out.append("wireRun model=Icosahedron samples=1200 rate=44100 laps=0.5 depth=1 s0=0 s1=0 s2=0 ev=600:model:Nonsense")
    for shape in ("sine", "triangle", "ramp", "square", "random"):
        for hz, seed in ((0.2, 1), (7.0, 9), (300.0, 4)):
            out.append("lfoRun %s %r %d 2000 48000" % (shape, hz, seed))
    return out

PLANE_DEFAULTS = dict(rate=48000.0, samples=2600, planeMirror=0, planeRadius=0.4, planeOS=2, planeLimit=0,
                      planeScaleX=1, planeScaleY=1, planeShear=0, planeTwist=0, planeKaleido=0, planeSnap=0,
                      delayMix=0, delayMs=375, delayFeedback=0.35, delayPingPong=0, chorusMix=0, chorusRate=0.6,
                      chorusDepthMs=3, chorusMs=12, chorusFeedback=0, twr=0, ecr=0, rpush=0, tpush=0, epush=0,
                      etpush=0, inp=0, ev="")

def plane_call(over):
    p = dict(PLANE_DEFAULTS); p.update(over)
    return "planeRun " + " ".join("%s=%s" % (k, v if isinstance(v, str) else repr(v)) for k, v in p.items())

def plane_scenarios():
    """Every stage of the plane alone at each oversampling, then together,
    then changed under the pairs. The pairs are a 220 and 661 Hz mix against
    330 Hz: never a circle, so a turn of the plane is a change of the figure
    (see CLAUDE.md on fixtures), and loud enough to reach the radius."""
    out = []
    stages = [dict(planeMirror=1), dict(planeMirror=2), dict(planeMirror=3), dict(planeTwist=1.5, tpush=0.6),
              dict(planeKaleido=3), dict(planeKaleido=5.5), dict(planeLimit=1, planeRadius=0.3, rpush=0.5),
              dict(planeLimit=2, planeRadius=0.25, rpush=0.3), dict(planeSnap=3), dict(planeSnap=6.5)]
    for os_ in (1, 2, 4):
        for s in stages:
            out.append(dict(planeOS=os_, **s))
    out.append(dict(planeScaleX=1.4, planeScaleY=-0.6, planeShear=0.5))
    # A pair held at -1.5 and 2.5 steps of a quarter's grid: halves, where
    # JavaScript's rounding takes -1.5 up to -1 and C++'s std::round takes it
    # down to -2. A sine passes through a half only by accident.
    out.append(dict(planeOS=1, planeSnap=3, inp=1, samples=200))
    out.append(dict(planeTwist=0, twr=1, tpush=0.9))
    # The echo short enough to come back inside the run, its time moved by a
    # routing (the read glides), ping-pong and not, and brought in from none.
    for pp in (0, 1):
        out.append(dict(delayMix=0.5, delayMs=12, delayFeedback=0.6, delayPingPong=pp, etpush=0.7))
    out.append(dict(delayMix=0, ecr=1, epush=0.9, delayMs=9))
    out.append(dict(chorusMix=0.7, chorusRate=3, chorusDepthMs=3, chorusMs=12, chorusFeedback=0.5))
    out.append(dict(chorusMix=1, chorusRate=40, chorusDepthMs=20, chorusMs=40, rate=44100.0))
    out.append(dict(planeMirror=1, planeTwist=0.8, planeKaleido=4, planeLimit=1, planeRadius=0.35, planeSnap=5,
                    planeScaleX=1.2, planeShear=-0.3, delayMix=0.4, delayMs=8, chorusMix=0.5, chorusRate=2,
                    tpush=0.4, rpush=0.4, epush=0.3, etpush=0.3, planeOS=4))
    # Changed under the pairs: the oversampling (its histories emptied each
    # time), the chorus brought in and the echo let go and brought back.
    out.append(dict(planeTwist=1.2, ev="300:planeOS:4;900:planeOS:1;1400:planeOS:2;1700:planeOS:4"))
    out.append(dict(planeLimit=2, planeRadius=0.3, delayMix=0.3, delayMs=6,
                    ev="500:chorusMix:0.6;1000:delayMix:0;1200:delayMix:0.5;1900:planeKaleido:3"))
    return out

VOICE_DEFAULTS = dict(rate=48000.0, samples=2400, seed=5, layer="a", shape="sine", amp=0.5, a=5, d=200, s=0.7, r=200,
                      fa=5, fd=200, fs=1, fr=200, vtype=0, vcut=2000, vq=0.7071, vtrack=0, venv=0, drive=0, fold=0,
                      cbits=0, chz=0, n=1, cents=0, fm=0, mod=1, ring=0, sync=1, sub=0, suboct=1, subsine=0,
                      width=0.25, table=1.5, morph=0, qmask=0, qglide=1, factor=2, fmr=0, syncr=0, shr=0, vpush=0,
                      dp=0, fp=0, bars="-", amount=0, bend=1, bend2=1, duck=0.9,
                      glide=1 - math.exp(-1 / 240), ev="0:none")

def voices_call(over):
    p = dict(VOICE_DEFAULTS); p.update(over)
    return "voicesRun " + " ".join("%s=%s" % (k, v if isinstance(v, str) else repr(v)) for k, v in p.items())

def chord(*notes):
    """`chord((60, 'x'), (64, 'y', 0.6))`: notes by MIDI number, equal-tempered."""
    return "+".join("%d/%r/%r/%s" % (n[0], 440 * 2 ** ((n[0] - 69) / 12), n[2] if len(n) > 2 else 1.0, n[1])
                    for n in notes)

def voice_scenarios():
    """The chord's voices, weighted towards the bookkeeping, which is where a
    port of `reconcileVoices` goes wrong: a note kept while the chord around
    it changes, a role changed under a held note (the gains glide), a key let
    go and pressed again inside its own release (a second voice, not the
    first one woken), a run of chords fast enough to put more than eight
    tails in flight, a layer switched off with notes held, the governor's
    cut, and two of one note in one list. Then every branch of `sound`."""
    C, E, G, B = 60, 64, 67, 71
    out = []
    out.append(dict(ev=";".join(["0:" + chord((C, "x"), (E, "y", 0.7), (G, "u")),
                                 "600:" + chord((C, "xy"), (E, "y", 0.7), (B, "x", 0.4)),
                                 "1100:" + chord((B, "q")), "1600:none"])))
    out.append(dict(ev=";".join(["0:" + chord((C, "x")), "500:none", "700:" + chord((C, "x", 0.5)), "1500:none"]),
                    r=400))
    # Six chords forty samples apart, three new notes each: fifteen tails.
    out.append(dict(r=900, ev=";".join("%d:%s" % (40 * k, chord(*[(48 + 3 * k + j, "xy"[j % 2]) for j in range(3)]))
                                       for k in range(6)) + ";260:none"))
    out.append(dict(ev="0:" + chord((C, "x"), (G, "y")) + ";700:null;900:" + chord((E, "xy"))))
    # One key held while its pitch is retuned under it: the same voice, at
    # the new pitch.
    out.append(dict(ev="0:60/261.63/1.0/x+67/392.0/1.0/y;500:60/270.0/1.0/x+67/392.0/1.0/y;1500:none"))
    out.append(dict(ev="0:" + chord((C, "x"), (E, "y"), (G, "xy")) + ";300:cut:1;400:none;500:cut:0;2000:cut:2"))
    out.append(dict(ev="0:" + chord((C, "x"), (C, "y", 0.3)) + ";0:" + chord((C, "xy"), (E, "x", 0)) + ";900:none"))
    # The quantiser, on C major with a glide, under a bend of two semitones:
    # off-key notes land on the key, then step as the bend carries them.
    out.append(dict(qmask=2741, qglide=0.004, bend=1.0, bend2=2 ** (2 / 12), samples=4800,
                    ev="0:" + chord((61, "x"), (66, "y"), (C, "u")) + ";3000:none"))
    out.append(dict(qmask=2741, qglide=1, bend=0.97, bend2=1.05, rate=44100.0, samples=3000,
                    ev="0:" + chord((C, "x"), (E, "y"))))
    # A key a fifth of a billionth of a semitone above the middle of C and D:
    # a tie, as the page counts one, which goes to the lower note.
    tie = 440 * 2 ** ((61 + 2e-10 - 69) / 12)
    out.append(dict(qmask=2741, ev="0:61/%r/1.0/x+62/%r/1.0/y" % (tie, 440 * 2 ** (-7 / 12))))
    # A bend carried through nought to below it, so the phase runs backwards:
    # the quantiser lets a pitch that is not above nought through untouched.
    out.append(dict(qmask=2741, bend=1.0, bend2=-1.0, shape="ramp",
                    ev="0:" + chord((C, "x"), (G, "y")) + ";1800:none"))
    for shape, seed in (("noise", 1), ("pink", 7), ("brown", 11), ("stepped", 13)):
        out.append(dict(shape=shape, seed=seed, ev="0:" + chord((C, "x"), (G, "y")) + ";800:" + chord((E, "xy")) + ";1600:none"))
    weights = ",".join("%r" % w for w in (0.1, 0, 0.3, 0.2, 0, 0.05, 0, 0, 0.35))
    for shape, extra in (("square", {}), ("ramp", {}), ("triangle", {}), ("harmonic", {}), ("pulse", dict(amount=0.3)),
                         ("morph", dict(amount=1.6)), ("drawbars", dict(bars=weights))):
        two = "0:" + chord((E, "x"), (B, "y", 0.8)) + ";1400:none"
        out.append(dict(shape=shape, ev=two, **extra))
        # The oscillator on: unison, FM, a sub and hard sync together.
        out.append(dict(shape=shape, ev=two, n=3, cents=12, fm=0.8, mod=2, sub=0.4, sync=1.5, syncr=1, **extra))
    shaped = "0:" + chord((C, "x"), (G, "y", 0.6)) + ";1200:none"
    for factor in (2, 4):
        out.append(dict(shape="square", factor=factor, drive=0.5, fold=0.2, dp=0.1, fp=-0.05, ev=shaped))
    out.append(dict(shape="ramp", shr=1, dp=0.4, ev=shaped))
    # The oversampling changed mid-note, as the governor changes it: each
    # voice's shaper is built again at the new factor.
    out.append(dict(shape="square", drive=0.6, factor=4, ev=shaped + ";700:factor:2"))
    out.append(dict(shape="triangle", cbits=5, chz=7000.0, ev=shaped))
    # The filter with its envelope, on both layers: on layer B the other
    # layer's filter envelope is different (see the runner), so the page's
    # choice of view is in the comparison.
    for layer in ("a", "b"):
        out.append(dict(layer=layer, shape="ramp", vtype=1, vcut=400, vq=2.0, venv=2.5, vtrack=0.5, fa=20, fd=150,
                        fs=0.3, fr=300, vpush=0.2, bend2=1.06, ev=shaped))
    out.append(dict(shape="square", vtype=3, vcut=1500, venv=-1, fa=1, fd=60, fs=0, fr=40, drive=0.3, cbits=7,
                    ev=shaped, layer="b"))
    # Sliders moved mid-note and mid-release: the envelopes read their tone
    # per sample, which is what holding the tone by pointer is for.
    out.append(dict(shape="ramp", vtype=1, vcut=600, venv=1.5, ev=";".join([
        "0:" + chord((C, "x"), (E, "y")), "60:set:attackMs:80", "700:set:sustain:0.3", "750:set:fSustain:0.1",
        "900:set:vcfCutoff:2400", "1000:none", "1200:set:releaseMs:40", "1300:set:fReleaseMs:900",
        "1400:set:amp:0.3"])))
    return out

lines = calls()
listed = os.path.join(BUILD, "calls.txt")
with open(listed, "w") as f: f.write("\n".join(lines) + "\n")
fexe = build("functions_cpp")
js_rows = subprocess.run(["node", os.path.join(HERE, "tools", "functions_js.mjs"), listed], check=True,
                         capture_output=True, text=True).stdout.splitlines()
cpp_rows = subprocess.run([fexe, listed], check=True, capture_output=True, text=True).stdout.splitlines()
def row(r): return [float(v) for v in r.split()]
by_name, worst_line = {}, ("", 0.0)
for call, a, b in zip(lines, js_rows, cpp_rows):
    w = worst(row(a), row(b))
    name = call.split()[0] + (" " + call.split()[1] if call.startswith(("waveAt", "noiseRun")) else "")
    if call.startswith("voicesRun"): name += " " + call.split(" shape=")[1].split()[0]
    if call.startswith("planeRun"): name += " at %sx" % call.split(" planeOS=")[1].split()[0]
    if call.startswith(("figureAt", "lfoRun")): name += " " + call.split()[1]
    by_name[name] = max(by_name.get(name, 0.0), w)
    if w > worst_line[1]: worst_line = (call[:80], w)
check("every call answered by both: %d calls" % len(lines), len(js_rows) == len(cpp_rows) == len(lines),
      "%d from the page, %d from the port" % (len(js_rows), len(cpp_rows)))
# Held to the last bit, where the page's arithmetic is a known algorithm the
# port copies rather than a library call each side has its own of.
EXACT = {"hypot"}
for name in sorted(by_name):
    tol = 0 if name in EXACT else TOL
    check("%s, the same to %g" % (name, tol), by_name[name] <= tol, "worst %.3g" % by_name[name])
# The nulls: the page's answers a line out of step, and one call changed.
shifted = js_rows[1:] + js_rows[-1:]
check("and the comparison fails against the page's answers a line out of step",
      max(worst(row(a), row(b)) for a, b in zip(shifted, cpp_rows)) > 1e-3)
# From the low part of a cycle, where the level is the width's: at the top of
# a cycle a pulse narrower than a half is 0.9 whatever its width, and the
# first such call found there could not tell 0.3 from 0.31.
pulse = next(i for i, l in enumerate(lines) if l.startswith("waveAt pulse") and l.endswith(" 0.3")
             and 0.4 < (float(l.split()[2]) / TWO_PI) % 1 < 0.9)
# The voices: every run sounds on each of its four mixes, so no comparison of
# them is a comparison of silence.
quiet = [l[:60] for l, a in zip(lines, js_rows) if l.startswith("voicesRun")
         and min(max(abs(v) for v in row(a)[k::4]) for k in (2, 3)) < 0.05]
check("every chord sounds, heard left and right", not quiet, "; ".join(quiet[:2]))
pictured = [l for l, a in zip(lines, js_rows) if l.startswith("voicesRun")
            and min(max(abs(v) for v in row(a)[k::4]) for k in (0, 1)) > 0.05]
check("and most draw on both picture channels", len(pictured) > 30, "%d" % len(pictured))
def js_one(call):
    return row(subprocess.run(["node", os.path.join(HERE, "tools", "functions_js.mjs"), _one(call)], check=True,
                              capture_output=True, text=True).stdout)
moved = next(i for i, l in enumerate(lines) if "set:releaseMs" in l)
check("and against a release slider that was never moved",
      worst(js_one(lines[moved].replace(";1200:set:releaseMs:40", "")), row(cpp_rows[moved])) > 1e-6)
onb = next(i for i, l in enumerate(lines) if l.startswith("voicesRun") and "layer=b" in l and "vtype=1" in l)
# What the page would have played had its layer-B voice read layer A's
# filter envelope: layer A, with A's times. The comparison has to fail on it.
check("and against layer B's filter envelope read from layer A's tone",
      worst(js_one(lines[onb].replace("layer=b", "layer=a").replace("fa=20 fd=150 fs=0.3 fr=300",
                                                                    "fa=1 fd=37 fs=0.2 fr=23")),
            row(cpp_rows[onb])) > 1e-6)
# The plane: every run changes layer A's pair somewhere, so no comparison is of
# the input passed through.
def plane_input(i, rate, held):
    if held: return -0.375, 0.625
    x = 0.7 * math.sin(TWO_PI * 220 * i / rate) + 0.25 * math.sin(TWO_PI * 661 * i / rate)
    return x, 0.5 * math.sin(TWO_PI * 330 * i / rate + 0.4)
still = []
for l, a in zip(lines, js_rows):
    if not l.startswith("planeRun"): continue
    rate, v, held = float(l.split("rate=")[1].split()[0]), row(a), " inp=1 " in l
    if max(max(abs(v[6 * i] - plane_input(i, rate, held)[0]), abs(v[6 * i + 1] - plane_input(i, rate, held)[1]))
           for i in range(len(v) // 6)) < 0.01:
        still.append(l[:70])
check("every plane run changes the pair it is given", not still, "; ".join(still[:2]))
kal = next(i for i, l in enumerate(lines) if "planeKaleido=5.5" in l)
check("and against a kaleidoscope of 5.6 answered as one of 5.5",
      worst(js_one(lines[kal].replace("planeKaleido=5.5", "planeKaleido=5.6")), row(cpp_rows[kal])) > 1e-6)
flips = next(i for i, l in enumerate(lines) if "900:planeOS:1" in l)
check("and against an oversampler that kept its history through a change of factor",
      worst(js_one(lines[flips].replace(";1700:planeOS:4", ";1700:planeOS:2")), row(cpp_rows[flips])) > 1e-6)
# The drawings: a solid that was never reset mid-lap, and a random LFO drawing
# from another seed, must both be told apart.
walk = next(i for i, l in enumerate(lines) if "1900:reset" in l)
check("and against a solid that was not reset mid-lap",
      worst(js_one(lines[walk].replace(";1900:reset", "")), row(cpp_rows[walk])) > 1e-6)
held = next(i for i, l in enumerate(lines) if l.startswith("lfoRun random 300.0"))
check("and against a random LFO from another seed",
      worst(js_one(lines[held].replace(" 4 2000", " 5 2000")), row(cpp_rows[held])) > 1e-6)
check("and against a pulse of 0.3 answered as one of 0.31",
      worst(row(subprocess.run(["node", os.path.join(HERE, "tools", "functions_js.mjs"),
                                _one(lines[pulse][:-3] + "0.31")], check=True, capture_output=True, text=True).stdout),
            row(cpp_rows[pulse])) > 1e-6)

print("\n--- the whole generator ---")
# Slots, as GEN_DESTS has them.
FREQ, AMP, PHASE, RATIO, DETAIL, TUMBLE, DEPTH, BAR = 0, 1, 2, 3, 4, 5, 6, 7
MORPH, RADIUS, TWIST, FM, SYNC, DRIVE, FOLD, VCF, ECHO, ECHOT, SWING, WIDTH, TABLE, SPIN = range(16, 30)

def route(slot, amount, index=-1, held=0, heldB=None, amountB=None, unipolar=0):
    return "%d/%r/%r/%d/%r/%r/%d" % (index, held, held if heldB is None else heldB, slot, amount,
                                     amount if amountB is None else amountB, unipolar)

def notes(*ns):
    return "+".join("%d/%r/%r/%s" % (n[0], 440 * 2 ** ((n[0] - 69) / 12), n[2] if len(n) > 2 else 1.0, n[1]) for n in ns)

def gen_runs():
    """The page's makeGeneratorCore and the port, driven alike: every mode,
    each feature in it, and the calls a worklet makes between blocks - the
    routings, the chord, the gate, a strike, a kick, a reswing - landing
    while things sound."""
    grng = random.Random(7)
    def tset():
        sizes = [16, 8, 4, 2]
        return "T:%d:%s" % (8, ";".join(",".join("%r" % (grng.randint(-64, 64) / 64) for _ in range(n)) for n in sizes))
    bank = "B:" + "!".join(tset()[2:] for _ in range(4))
    runs = []
    def add(name, events, samples=4096, rate=48000.0, slots=32, seed=3, lfo0="sine,5", lfo1="triangle,0.7"):
        runs.append((name, "run name=%s rate=%r slots=%d seed=%d samples=%d lfo0=%s lfo1=%s\n%s\nend"
                     % (name, rate, slots, seed, samples, lfo0, lfo1, "\n".join("at %d %s" % e for e in events))))
    vib = route(FREQ, 0.05, index=0)
    # A key held at the end, gated, so the envelope as a source reads where the ADSR has got to rather than nought.
    add("env-held", [(0, "gated 1"), (256, "gate 1 0.8")])
    # The dyad, every shape, gliding to a new pitch with a vibrato on it.
    for shape in ("harmonic", "sine", "triangle", "square", "ramp", "pulse", "morph", "noise", "pink", "brown", "stepped"):
        add("dyad-" + shape, [(0, "set shape " + shape), (0, "set glideMs 30"), (0, "routes " + vib),
                              (1024, "set freq 331"), (2048, "set interval 7"), (2048, "set just false"),
                              (3072, "set octaves 1")])
    add("dyad-drawbars", [(0, "set shape drawbars"), (0, "bars 0 8,0,6,3,0,2,0,1,4"),
                          (0, "routes " + "+".join([route(BAR + 2, 0.4, index=1), route(BAR + 7, -0.3, index=0)])),
                          (2048, "bars 0 0,0,8,0,0,0,0,0,0"), (3072, "bars 0 12,-3,11,0,9.5,0,0,-4,2"),
                          # Pushes held back across the ends: an 11 pushed down by four is 7 if
                          # it was kept as 11, and 4 if it was clamped to 8 when it was set.
                          (3072, "routes " + "+".join([route(BAR + 2, -0.5, held=1), route(BAR + 7, 0.4, held=1)]))])
    add("dyad-drawn", [(0, "set shape drawn"), (0, "cycle " + tset()), (2048, "set freq 1700")])
    # An oscillator's shape changed in the middle, under a routing: the
    # compiled core is told a shape only when it changes, and one never told
    # went on with the old.
    # And restarted, as the worklet restarts one when the page's is: by
    # setting its phase to nought, which the compiled core has to be told.
    add("dyad-lfo-restart", [(0, "routes " + route(FREQ, 0.2, index=0)), (1536, "restart 0"), (2944, "restart 0")])
    add("dyad-lfo-shape", [(0, "routes " + route(FREQ, 0.2, index=0)), (1536, "lfo 0 square 9"), (3072, "lfo 0 random 40")])
    add("dyad-wavetable", [(0, "set shape wavetable"), (0, "wavetable " + bank), (0, "routes " + route(TABLE, 0.8, index=1))])
    # On the bank's last slot and nowhere else, so a bank that arrived a slot
    # short - which the compiled core's numbers once could - is heard.
    add("dyad-wavetable-last", [(0, "set shape wavetable"), (0, "wavetable " + bank), (0, "set table 3")])
    # Each of the three taken away again, as the page takes them: a cycle, a
    # bank or a path cleared that the core went on drawing passed until these.
    add("dyad-drawn-cleared", [(0, "set shape drawn"), (0, "cycle " + tset()), (2048, "cycle none")])
    add("dyad-wavetable-cleared", [(0, "set shape wavetable"), (0, "wavetable " + bank), (2048, "wavetable none")])
    add("dyad-shape-routes", [(0, "set shape pulse"), (0, "routes " + "+".join([route(WIDTH, 0.6, index=0),
                              route(PHASE, 0.3, index=1), route(RATIO, 0.2, held=0.5), route(AMP, 0.5, index=0, unipolar=1)])),
                              (2048, "set shape morph"), (2048, "routes " + route(MORPH, 0.9, index=1))])
    # The voice: its oscillator, its shaping at both factors, crush, filter.
    add("dyad-voice", [(0, "set shape ramp"), (0, "set unison 5"), (0, "set unisonCents 20"), (0, "set fmIndex 1.5"),
                       (0, "set modRatio 2"), (0, "set subLevel 0.5"), (0, "set subOctave 2"), (0, "set subShape sine"),
                       (1024, "set syncRatio 1.7"), (1024, "routes " + "+".join([route(FM, 0.5, index=0),
                       route(SYNC, 0.3, index=1)])), (2048, "set ringMix 0.4"), (3072, "reswing")])
    add("dyad-shaped", [(0, "set shape square"), (0, "set drive 0.6"), (0, "set fold 0.3"), (0, "set shapeOS 4"),
                        (0, "set crushBits 6"), (0, "set crushHz 9000"), (1024, "routes " + route(DRIVE, 0.4, index=0)),
                        (2048, "set shapeOS 2"), (3072, "set fold 0")])
    add("dyad-filter-gated", [(0, "set shape ramp"), (0, "set vcfType 1"), (0, "set vcfCutoff 500"), (0, "set vcfEnv 3"),
                              (0, "set vcfTrack 0.5"), (0, "set vcfQ 3"), (0, "gated 1"), (256, "gate 1 0.8"),
                              (0, "set interval 7"),
                              (1536, "routes " + route(VCF, 0.4, index=0)), (2560, "gate 0 0"), (3584, "gate 1 0.5"),
                              (3840, "gated 0")])
    # Not gated, and the gate pressed anyway: the filter's envelope moves,
    # and an ungated dyad must not read it.
    add("dyad-filter-ungated", [(0, "set shape ramp"), (0, "set vcfType 1"), (0, "set vcfCutoff 500"),
                                (0, "set vcfEnv 3"), (256, "gate 1 1"), (2048, "gate 0 0")])
    # Fold alone routed, with drive and fold at rest: the shaper is still on.
    add("dyad-fold-routed", [(0, "set shape triangle"), (0, "routes " + route(FOLD, 0.8, index=0))])
    # A ratio pushed below nought, so the right channel's phase runs backwards.
    add("dyad-negative-ratio", [(0, "set shape ramp"), (0, "routes " + route(RATIO, -3.0, held=1))])
    add("dyad-quantised", [(0, "set qMask 2741"), (0, "set qGlideMs 15"), (0, "set freq 277"),
                           (0, "routes " + route(FREQ, 0.3, index=1)), (2048, "set qGlideMs 0")], lfo1="sine,3")
    add("dyad-random-lfo", [(0, "routes " + "+".join([route(FREQ, 0.2, index=0), route(AMP, 0.6, index=1, unipolar=1)]))],
        lfo0="random,40", lfo1="square,9")
    add("dyad-few-slots", [(0, "set shape morph"), (0, "routes " + "+".join([route(MORPH, 0.9, index=0),
                           route(FREQ, 0.1, index=1), route(30, 1.0, held=1)]))], slots=8)
    # The chord, on one layer and on two, roles changing under it; then the
    # governor: everything on at once, past its budget, then the chord changed.
    add("poly", [(0, "voices 0 " + notes((60, "x"), (64, "y", 0.7), (67, "u"))), (0, "routes " + vib),
                 (0, "set releaseMs 6"),
                 (1024, "voices 0 " + notes((60, "xy"), (64, "y", 0.7), (71, "x"))), (2048, "voices 0 none"),
                 (3072, "voices 0 " + notes((62, "x")))])
    add("layered", [(0, "voices 0 " + notes((48, "x"), (55, "y"))), (0, "voices 1 " + notes((72, "xy"), (76, "u"))),
                    (0, "set shape square 1"), (0, "set attackMs 40 1"), (0, "set releaseMs 30 1"),
                    (0, "routes " + "+".join([route(FREQ, 0.05, index=0, amountB=0.2), route(DRIVE, 0.0, amountB=0.5, held=1),
                                              route(FM, 0.3, amountB=-0.2, index=1)])),
                    (0, "set drive 0.3 1"), (0, "set fmIndex 1 1"),
                    # Fields layer B does not have are not written into A by a set on B.
                    (512, "set freq 500 1"), (512, "set planeTwist 1.5 1"), (512, "set mode figure 1"), (512, "set amp 0.3"),
                    # A held routing that holds one value for A and another for B.
                    (1024, "routes " + route(FREQ, 0.25, held=0.2, heldB=-0.6)),
                    (1536, "voices 1 " + notes((74, "x"))), (2560, "voices 1 null"), (3072, "voices 1 " + notes((79, "y")))])
    # Drawbars on both layers with two registrations, which no run had: a
    # registration given to B that landed on A, or nowhere, passed.
    add("layered-drawbars", [(0, "voices 0 " + notes((48, "x"), (55, "y"))), (0, "voices 1 " + notes((67, "xy"))),
                             (0, "set shape drawbars"), (0, "set shape drawbars 1"),
                             (0, "bars 0 8,0,6,3,0,2,0,1,4"), (0, "bars 1 0,8,0,0,5,0,3,0,0"),
                             (2048, "bars 1 2,0,0,8,0,0,0,6,0")])
    chord = notes(*[(48 + 3 * k, "xyu"[k % 3]) for k in range(8)])
    add("governed", [(0, "set unison 7"), (0, "set unisonCents 25"), (0, "set fmIndex 2"), (0, "set syncRatio 1.5"),
                     (0, "set drive 0.5"), (0, "set shapeOS 4"), (0, "set vcfType 2"), (0, "set crushBits 8"),
                     (0, "voices 0 " + chord), (0, "voices 1 " + chord), (0, "set unison 7 1"), (0, "set fmIndex 2 1"),
                     (0, "set planeKaleido 3"), (0, "set planeOS 4"),
                     (1024, "voices 0 " + notes((60, "x"), (64, "y"))), (2048, "set unison 3"), (3072, "voices 1 none")],
        samples=4096)
    # And held there to the end, so the report the run ends with is the
    # governor's answer to the whole chord on both layers.
    add("governed-held", [(0, "set unison 7"), (0, "set unisonCents 25"), (0, "set fmIndex 2"), (0, "set syncRatio 1.5"),
                          (0, "set drive 0.5"), (0, "set shapeOS 4"), (0, "set vcfType 2"), (0, "voices 0 " + chord),
                          (0, "voices 1 " + chord), (0, "set unison 7 1"), (0, "set fmIndex 2 1"), (0, "set drive 0.5 1")],
        samples=2048)
    # The costs of each shape's copies and single path, reported by the budget.
    for sa, sb in (("morph", "drawbars"), ("pulse", "wavetable")):
        add("governed-%s" % sa, [(0, "set shape " + sa), (0, "set shape %s 1" % sb), (0, "set unison 3"),
                                 (0, "set unison 2 1"), (0, "voices 0 " + notes((60, "x"), (64, "y"))),
                                 (0, "voices 1 " + notes((72, "xy"))), (0, "wavetable " + bank)], samples=2048)
        add("governed-%s-single" % sa, [(0, "set shape " + sa), (0, "set shape %s 1" % sb),
                                        (0, "voices 0 " + notes((60, "x"), (64, "y"))),
                                        (0, "voices 1 " + notes((72, "xy"))), (0, "wavetable " + bank)], samples=1024)
    # Twelve shaped voices: four times the rate is over the budget at 30 a
    # voice and inside it at 17, so the factor given up says which.
    six = notes(*[(50 + 2 * k, "xy") for k in range(6)])
    add("governed-factor", [(0, "set drive 0.5"), (0, "set drive 0.5 1"), (0, "set shapeOS 4"), (0, "voices 0 " + six),
                            (0, "voices 1 " + six)], samples=1024)
    # Caps that stay down while tails die away: a chord let go to two notes,
    # its six tails gone inside a few blocks, and the copies not given back.
    tails = [(0, "set unison 7"), (0, "set fmIndex 2"), (0, "set syncRatio 1.5"), (0, "set drive 0.5"),
             (0, "set vcfType 1"), (0, "set crushBits 6"), (0, "set subLevel 0.4"), (0, "set ringMix 0.3"),
             # The plane, costed per pass and a chord is two passes, so cutting voices is needed even at one copy.
             (0, "set planeKaleido 3"), (0, "set planeOS 4"), (0, "set delayMix 0.3"),
             (0, "set releaseMs 4"), (0, "voices 0 " + chord), (512, "voices 0 " + notes((60, "x"), (64, "y")))]
    add("governed-tails", tails, samples=2048)
    # And the block right after the let-go, while the tails cut are still fading.
    add("governed-cut", tails, samples=640)
    # The drawings.
    for fig in ("Circle", "Square", "Polygon", "Star", "Rose", "Heart", "Infinity", "Spiral", "Spirograph", "Butterfly"):
        add("figure-" + fig, [(0, "set mode figure"), (0, "set figure " + fig), (0, "set figureRate 170"),
                              (0, "routes " + route(DETAIL, 0.4, index=1)), (2048, "set detail 7.5")])
    add("figure-path", [(0, "set mode figure"), (0, "set figure Text"),
                        (0, "figPath P:-0.5,0.2,0.3,0.8,0.9,-0.4,-0.1,-0.7,0.4,0.1,-0.5,0.2;0,0.18,0.5,0.5,0.86,1"),
                        (0, "set figureRate 90")])
    # This run's path had a time more than it had points, by mistake, for as
    # long as it has existed; the page drew NaN for the last stretch and the
    # core read past its vector, and a comparison that skipped NaN called
    # them the same. The short path is held at figureAt now, where NaN is
    # compared as NaN. Not here: the generator's output is clamped, with
    # fmin and fmax in the core, which take the bound for a NaN, and with
    # Math.min and Math.max on the page, which keep it - so a NaN sample is
    # full scale in one and NaN in the other. The core's is the safer for a
    # host, and nothing the page builds makes a NaN to reach it.
    add("figure-path-cleared", [(0, "set mode figure"), (0, "set figure Path"),
                                (0, "figPath P:-0.5,0.2,0.3,0.8,0.9,-0.4,-0.1,-0.7,0.4,0.1,-0.5,0.2;0,0.18,0.5,0.5,0.86,1"),
                                (0, "set figureRate 90"), (2048, "figPath none")])
    add("figure-rose-turns", [(0, "set mode figure"), (0, "set figure Rose"), (0, "set detail 2.37"),
                              (0, "set figureRate 2400")], samples=6144)
    for model in ("Cube", "Tetrahedron", "Octahedron", "Dodecahedron", "Icosahedron", "Torus", "Knot"):
        add("solid-" + model, [(0, "set mode wireframe"), (0, "set model " + model), (0, "set figureRate 60"),
                               (0, "routes " + "+".join([route(TUMBLE, 0.5, index=0), route(DEPTH, 0.6, index=1),
                                                         route(SPIN + 1, 0.8, index=1)])),
                               (1024, "kick 2"), (2048, "spin 0.5,-0.2,0.9"), (3072, "kick -1.5")], lfo0="sine,2")
    # Run down inside the run (a decay of 40 is a fortieth of a second a
    # neper), so it is let go again and the relet's fade is in the output;
    # then struck, then driven.
    add("swing", [(0, "set mode harmonograph"), (0, "set decay 40"), (0, "set swingRate 40"), (0, "set detune 0.02"),
                  (5248, "reswing"), (5632, "set swingDrive 0.5"), (5632, "routes " + route(SWING, 0.5, index=1)),
                  (6400, "set swingDrive 0"), (6400, "routes none")],
        samples=7168)
    # A change of mode lets the pendulums go again, mid-swing.
    add("swing-mode", [(0, "set mode harmonograph"), (0, "set decay 3"), (0, "set swingRate 30"),
                       (1536, "set mode figure"), (2048, "set mode harmonograph")])
    add("swing-pitched", [(0, "set mode harmonograph"), (0, "set pitched true"), (0, "set ringMs 40"),
                          (0, "set freq 330"), (0, "set qMask 2741"), (1024, "reswing"), (2048, "set freq 290"),
                          (2560, "reswing"), (3584, "set decay 0.5")])
    # The plane on a dyad and on a chord, where the heard pair is its own.
    add("plane-dyad", [(0, "set planeTwist 0.9"), (0, "set planeLimit 1"), (0, "set planeRadius 0.3"),
                       (0, "set chorusMix 0.5"), (0, "set chorusRate 3"), (0, "set delayMix 0.4"), (0, "set delayMs 9"),
                       (0, "routes " + "+".join([route(RADIUS, 0.4, index=0), route(ECHOT, 0.3, index=1)]))])
    add("plane-poly", [(0, "voices 0 " + notes((60, "x"), (67, "y"), (64, "u"))), (0, "voices 1 " + notes((76, "xy"))),
                       (0, "set planeMirror 1"), (0, "set planeKaleido 4"), (0, "set delayMix 0.3"), (0, "set delayMs 7"),
                       (0, "routes " + "+".join([route(TWIST, 0.6, index=0), route(ECHO, 0.5, index=1)]))])
    # The crossings, the score, and the input three ways and from the second generator.
    add("crossings", [(0, "set mode figure"), (0, "set figureRate 30"), (0, "set crossOn true"), (0, "set crossX 0.2"),
                      (0, "set crossY -0.3"), (0, "set crossDecayMs 40"), (0, "set scoreDecayMs 10"), (2048, "strike 440 0.8"), (2560, "strike 550 1"),
                      (2688, "strike 660 0.4"), (2816, "strike 880 0.9"), (2944, "strike 990 0.7")], samples=8192)
    # The harmonic's two peaks either side of a dip, the line between the dip
    # and five hundredths above it: the beam falls below the line without
    # falling far enough to arm it again, and the peaks are 50 ms apart.
    add("crossings-dip", [(0, "set freq 5"), (0, "set crossOn true"), (0, "set crossX 0.39"), (0, "set crossY 0.9")],
        samples=12288)
    # A clock input that never goes below nought: it dips into the
    # hysteresis and out again, which re-arms nothing.
    add("input-clock-dc", [(0, "input 97 0.295 0.3"), (0, "set inputMode 3"), (0, "set mode figure")])
    for mode in (1, 2, 3):
        add("input-%d" % mode, [(0, "input 97 0.6"), (0, "set inputMode %d" % mode), (0, "set inputDepth 0.4"),
                                (0, "set mode figure"), (2048, "set mode wave"), (3072, "input 0 0")])
    add("input-ride-poly", [(0, "input 61 0.5"), (0, "set inputMode 2"), (0, "voices 0 " + notes((60, "x"), (64, "u")))])
    for mode in (1, 2, 3):
        add("gen2-%d" % mode, [(0, "set inputFrom gen2"), (0, "set inputMode %d" % mode), (0, "set gen2Figure Star"),
                               (0, "set gen2Rate 73"), (0, "set mode figure"), (2048, "set mode wave"),
                               (3072, "set gen2Rate 70000")])
    add("effect", [(0, "fx 1"), (0, "input 140 0.7"), (0, "set planeTwist 0.7"), (0, "set chorusMix 0.6"),
                   (0, "routes " + route(TWIST, 0.5, index=0)), (2048, "set planeSnap 4")])
    # More of the effect, now that the compiled core plays it too: the echo
    # with feedback and ping-pong under a routing on its level and time, the
    # kaleidoscope and the mirror oversampled four times with the radius
    # routed, and nothing on at all - the input handed through untouched.
    add("effect-echo", [(0, "fx 1"), (0, "input 220 0.6"), (0, "set delayMix 0.4"), (0, "set delayMs 9"),
                        (0, "set delayFeedback 0.6"), (0, "set delayPingPong true"),
                        (0, "routes " + "+".join([route(ECHO, 0.5, index=1), route(ECHOT, 0.3, index=0)])),
                        (1536, "restart 0"), (2048, "input 0 0")])
    add("effect-kaleido", [(0, "fx 1"), (0, "input 330 0.8 0.1"), (0, "set planeKaleido 5"), (0, "set planeMirror 1"),
                           (0, "set planeOS 4"), (0, "routes " + route(RADIUS, 0.4, index=0)), (2048, "set planeKaleido 3")])
    add("effect-off", [(0, "fx 1"), (0, "input 180 0.7"), (2048, "input 90 0.3 -0.2")])
    add("at-44100", [(0, "set shape square"), (0, "set unison 3"), (0, "routes " + vib)], rate=44100.0)
    return runs

runs = gen_runs()
listed = os.path.join(BUILD, "generator.txt")
with open(listed, "w") as f: f.write("\n".join(r for _, r in runs) + "\n")
gexe = build("generator_cpp")
gjs = subprocess.run(["node", os.path.join(HERE, "tools", "generator_js.mjs"), listed], check=True,
                     capture_output=True, text=True).stdout.splitlines()
gcpp = subprocess.run([gexe, listed], check=True, capture_output=True, text=True).stdout.splitlines()
check("every run answered by both: %d runs" % len(runs), len(gjs) == len(gcpp) == len(runs))
gworst = {}
for (name, _), a, b in zip(runs, gjs, gcpp):
    family = name.split("-")[0]
    gworst[family] = max(gworst.get(family, 0.0), worst(row(a), row(b)))
for family in sorted(gworst):
    check("%s, the same to %g" % (family, TOL), gworst[family] <= TOL, "worst %.3g" % gworst[family])

# Each run has to be able to show what it is for: a comparison of two cores
# doing nothing would pass. The report at the end of a row is envelope, pitch,
# the two crossings' counts, the kick, the swing, then the budget (units,
# asked A and B, unison A and B, asked factor, factor, silenced), the drawing
# (swing, pendulum, three turns, facing), the voices on each layer, and then
# the sources that read the generator, the page's registrations against the
# core's: the note envelope and the drawings' six.
TAIL = 29
def grow(name):
    i = next(k for k, (n, _) in enumerate(runs) if n == name)
    v = row(gjs[i])
    return v[:-TAIL], v[-TAIL:]
def col(v, c): return v[c::6]
quiet = [n for n, _ in runs if max(abs(x) for x in col(grow(n)[0], 0)) < 0.01]
check("every run puts something on the screen", not quiet, ", ".join(quiet))
body, tail = grow("governed-held")
check("the governor, given everything, takes copies and voices away",
      tail[9] < tail[7] and tail[10] < tail[8] and tail[12] < tail[11] and tail[13] > 0,
      "asked %d/%d, given %d/%d, factor %d of %d, %d silenced" % (tail[7], tail[8], tail[9], tail[10], tail[12], tail[11], tail[13]))
body, tail = grow("crossings")
check("the crossings fire on both lines", tail[2] > 0 and tail[3] > 0, "%d and %d" % (tail[2], tail[3]))
body, _ = grow("layered")
check("layer B draws a picture of its own", max(abs(x) for x in col(body, 4)) > 0.05)
body, _ = grow("poly")
check("in a chord the heard pair is not the picture",
      max(abs(a - b) for a, b in zip(col(body, 0), col(body, 2))) > 0.05)
check("the second generator is drawn while there is no layer B", all(max(abs(x) for x in col(grow("gen2-%d" % m)[0], 4)) > 0.1
                                                                     for m in (1, 2, 3)))
_, tail = grow("solid-Cube")
check("a solid turns, and a kick is still spinning it", abs(tail[16]) + abs(tail[17]) > 0.01 and tail[4] != 0)
# The sources: a solid whose three turns all differ, so a swapped axis is not
# hidden; the envelope as a source somewhere non-zero; and somewhere ungated,
# where the generator reports one and the source has to read nought.
tails = {n: grow(n)[1] for n, _ in runs}
turned = [n for n, t in tails.items() if len({round(x, 9) for x in t[25:28]}) == 3 and min(abs(x) for x in t[25:28]) > 1e-3]
swung = [n for n, t in tails.items() if abs(t[23]) > 1e-3 and abs(t[24]) > 1e-3]
enveloped = [n for n, t in tails.items() if t[22] > 1e-3]
ungated = [n for n, t in tails.items() if t[0] == 1 and t[22] == 0]
check("the runs can show the sources: a solid's three turns apart, the pendulums swinging, an envelope, and an ungated one",
      turned and swung and enveloped and ungated, "%d, %d, %d, %d" % (len(turned), len(swung), len(enveloped), len(ungated)))
_, tail = grow("swing-pitched")
check("pitched, the pendulums sound at a quantised pitch", abs(12 * math.log2(tail[1] / 440) - round(12 * math.log2(tail[1] / 440))) < 1e-9
      and tail[1] > 200, "%.4f Hz" % tail[1])
# Nulls: the page told something different, and the port must disagree.
def gjs_one(text):
    path = os.path.join(BUILD, "one_gen.txt")
    with open(path, "w") as f: f.write(text + "\n")
    return row(subprocess.run(["node", os.path.join(HERE, "tools", "generator_js.mjs"), path], check=True,
                              capture_output=True, text=True).stdout)
def gnull(name, old, new, what):
    i = next(k for k, (n, _) in enumerate(runs) if n == name)
    assert old in runs[i][1], old
    check("and against " + what, worst(gjs_one(runs[i][1].replace(old, new)), row(gcpp[i])) > 1e-6)
gnull("poly", "/0.7/y", "/0.69/y", "a chord with one velocity a hundredth less")
gnull("input-3", "input 97 0.6", "input 98 0.6", "a clock a hertz faster")
gnull("governed-held", "set shapeOS 4", "set shapeOS 2", "a governor that never had four times to give up")
gnull("solid-Knot", "kick 2", "kick 2.01", "a kick a two-hundredth harder")
check("and the comparison fails against the page's runs a line out of step",
      min(worst(row(a), row(b)) for a, b in zip(gjs[1:] + gjs[:1], gcpp)) > 1e-3)

print("\n--- the keyboard ---")
# The page's own `midi` functions and scope::Keyboard, each playing a generator
# that writes down every call made of it, through the same commands. A line a
# command: what each call was, then the keyboard's sources, its readout, the
# panel it moved, the stack and the controllers. Compared word by word, and a
# number to 1e-12 - the frequencies come from `Math.pow` and `std::pow`.
kexe = build("keyboard_cpp")
import re
def ktoks(line): return [t for t in re.split(r"[\s/+]+", line) if t]
def kdiff(a, b):
    """The first line where the two disagree, or None."""
    a, b = a.strip().split("\n"), b.strip().split("\n")
    if len(a) != len(b): return "%d lines against %d" % (len(a), len(b))
    for i, (x, y) in enumerate(zip(a, b)):
        tx, ty = ktoks(x), ktoks(y)
        if len(tx) != len(ty): return "line %d: %s | %s" % (i, x[:160], y[:160])
        for p, q in zip(tx, ty):
            if p == q: continue  # minus infinity against itself is no difference, though their difference is NaN
            try:
                fp, fq = float(p), float(q)
                ok = (math.isnan(fp) and math.isnan(fq)) or abs(fp - fq) <= TOL * max(1.0, abs(fp))
            except ValueError: ok = p == q
            if not ok: return "line %d: %s against %s in %s" % (i, p, q, x[:160])
    return None
def kboth(text, name="keyboard_one.txt"):
    path = os.path.join(BUILD, name)
    with open(path, "w") as f: f.write(text)
    js = subprocess.run(["node", os.path.join(HERE, "tools", "keyboard_js.mjs"), path], check=True,
                        capture_output=True, text=True).stdout
    return js, subprocess.run([kexe, path], check=True, capture_output=True, text=True).stdout

def krun(*commands, head=""):
    return "run %s\n%s\nend\n" % (head, "\n".join(commands))

kruns = [
    ("dyad", krun("frame 16", "on 57 100", "on 64 90", "frame 16", "on 69 80", "off 69", "off 57", "off 64", "on 45 70",
                  "on 76 127", "frame 16", "off 45", "on 40 60", "on 79 61", "panic", "frame 16")),
    ("dyad-hold", krun("frame 16", "hold 1", "on 60 100", "on 67 100", "off 60", "off 67", "on 62 90", "hold 0", "off 62",
                       "on 62 90", "frame 16")),
    ("dyad-edges", krun("frame 16", "on 120 100", "on 127 100", "off 120", "off 127", "on 5 100", "on 0 1", "frame 16",
                        "on 60 0", "on 0 0", "on 64 50", "on 64 120", "frame 16")),
    ("mono", krun("frame 16", "on 60 100", "on 67 100", "mode mono", "on 72 100", "off 72", "off 67", "frame 16",
                  "mode dyad", "on 76 50", "panel interval 5", "mode mono", "frame 16")),
    ("poly-outer", krun("mode poly", "frame 16", "on 48 100", "on 64 90", "on 67 80", "on 72 70", "on 55 60", "frame 16",
                        "off 48", "off 72", "on 36 30", "frame 16")),
    ("poly-rules", krun("mode poly", "frame 16", "on 48 100", "on 52 91", "on 55 82", "on 59 73", "on 62 64", "on 65 55",
                        "draw 0 3 lowest", "draw 0 4 highest", "draw 0 2 recent", "draw 0 5 outer", "draw 0 0 outer",
                        "draw 0 99 lowest", "draw 0 1 recent", "draw 0 -3 highest", "frame 16")),
    ("poly-many", krun("mode poly", "frame 16", *["on %d %d" % (40 + 3 * k, 20 + 9 * k) for k in range(11)], "frame 16",
                       "off 43", "off 70", "frame 16", "draw 0 8 recent", "on 41 99")),
    # A count the page keeps as given, and slices by truncation: 2.6 draws two.
    ("poly-fractional", krun("mode poly", "frame 16", "on 48 100", "on 52 90", "on 55 80", "on 59 70", "on 62 60",
                             "draw 0 2.6 lowest", "draw 0 3.99 highest", "draw 0 2.5 recent", "draw 0 3.5 outer",
                             "draw 0 8.9 lowest", "frame 16")),
    ("poly-just", krun("mode poly", "frame 16", "just 1", "on 60 100", "on 64 100", "on 67 100", "on 81 100", "on 47 100",
                       "just 0", "frame 16", "just 1", "off 47", "off 60")),
    ("poly-one", krun("mode poly", "frame 16", "on 60 100", "off 60", "on 61 40", "frame 16", "mode dyad", "on 66 70",
                      "mode poly", "frame 16")),
    ("split", krun("mode poly", "frame 16", "layers split", "on 40 100", "on 47 90", "on 64 80", "on 72 70", "on 76 60",
                   "frame 16", "draw 1 2 highest", "draw 0 3 lowest", "pair against", "on 59 50", "on 60 51",
                   "pair each", "off 40", "off 72", "frame 16", "layers off", "frame 16")),
    ("split-learn", krun("mode poly", "frame 16", "layers split", "on 50 100", "on 70 100", "learn", "on 65 90",
                         "on 60 80", "frame 16", "learn", "learn", "on 30 10", "frame 16")),
    ("layer", krun("mode poly", "frame 16", "layers layer", "on 48 100", "on 55 90", "on 64 80", "pair against",
                   "frame 16", "draw 1 2 recent", "on 67 70", "mode dyad", "frame 16", "mode poly", "frame 16",
                   "layers split", "frame 16")),
    ("pedal", krun("frame 16", "on 60 100", "pedal 1", "off 60", "on 64 90", "off 64", "on 60 70", "frame 30",
                   "pedal 0", "frame 30", "pedal 0.5", "pedal 0.503937007874", "pedal 0.50393700787401574",
                   "on 67 90", "off 67", "frame 5", "pedal 0", "cc 64 127", "on 69 50", "off 69", "panic", "cc 64 0",
                   "frame 100")),
    ("pedal-poly", krun("mode poly", "frame 16", "on 48 100", "on 52 100", "pedal 1", "off 48", "off 52", "on 55 100",
                        "frame 16", "on 48 40", "pedal 0", "frame 16", "off 48", "off 55")),
    ("controllers", krun("frame 16", "cc 16 64", "frame 10", "cc 42 127", "frame 40", "cc 16 0", "cc 7 100",
                         "frame 1000", "name 42 Lower_drawbars", "name 99 Ninety_nine", "name 16", "cc 99 3", "cc 123 5", "on 60 80", "cc 120 0", "cc 113 1", "frame -5", "frame 0", "frame 3")),
    ("bytes", krun("frame 16", "bytes 0x90,60,100,64,90", "bytes 0x80,60,0", "bytes 0x90,67", "bytes 100",
                   "bytes 0x90,72,0xF8,77,0xFA,0xFB,0xFC", "bytes 0xB0,16,90,17,30,0xC0,5,0x90,62,0",
                   "bytes 1,2,3", "bytes 0xF2,1,2,64,90", "bytes 0x90,74,0x80,74,0", "bytes 0xD0,9,0x90,76,99",
                   "bytes 0xE0,0,64,0xB0,64,127", "bytes 0x99,30,10,0x8F,30,10,0xBF,123,0", "frame 16")),
    ("figure", krun("gen mode figure", "frame 16", "on 57 100", "on 64 100", "panel figureRate 120", "on 81 100",
                    "off 57", "play 1", "on 40 90", "play 0", "gen figure Rose", "on 52 100", "on 59 100",
                    "off 52", "panel detail 7", "on 40 50", "off 59", "hold 1", "on 47 40", "on 54 40",
                    "gen just false", "on 61 40", "on 40 100", "on 64 100", "mode mono", "on 71 40", "frame 16")),
    ("figure-far", krun("gen mode figure", "frame 16", "panel figureRate 200", "on 100 100", "play 1", "on 127 100",
                        "on 1 10", "play 0", "on 0 10", "frame 16")),
    ("harmonograph", krun("gen mode harmonograph", "frame 16", "on 57 100", "play 1", "on 64 90", "off 64",
                          "on 69 80", "drive 0", "on 72 70", "drive 1", "frame 16", "play 0", "on 74 60",
                          "frame 16")),
    ("wireframe", krun("gen mode wireframe", "frame 16", "on 57 100", "on 64 90", "drive 1", "on 69 80", "play 1",
                       "on 72 70", "drive 0", "on 76 60", "frame 16")),
    ("drive", krun("frame 16", "on 57 100", "on 64 90", "panel freq 330", "panel interval 4", "drive 0", "on 69 100",
                   "frame 16", "drive 1", "frame 16", "undrive", "mode mono", "frame 16", "on 60 100", "play 1")),
    ("kinds", krun("frame 16", "on 57 100", "gen mode figure", "frame 16", "on 64 90", "gen mode wave", "frame 16",
                   "mode poly", "gen mode harmonograph", "frame 16", "on 67 80", "gen mode wave", "frame 16",
                   "layers split", "gen mode figure", "frame 16", "gen mode wave", "frame 16")),
    ("absent", krun("frame 16", "on 57 100", "on 64 90", "mode poly", "frame 16", "present 1", "frame 16",
                    "on 67 80", "present 0", "frame 16", "layers split", "present 1", "frame 16", head="present=0")),
    ("second", krun("frame 16", "gen inputFrom gen2", "frame 16", "mode poly", "layers split", "on 40 100",
                    "on 70 100", "frame 16", "layers off", "frame 16", "gen inputFrom live", "frame 16")),
]

# And sequences no one wrote: seeded, so a failure is the same failure again.
krng = random.Random(95)
def kfuzz(n):
    out = ["frame 16"]
    held = []
    for _ in range(n):
        r = krng.random()
        if r < 0.32:
            note = krng.choice([krng.randint(30, 90), krng.choice([59, 60, 61]), krng.choice(held or [60])])
            out.append("on %d %d" % (note, krng.choice([krng.randint(1, 127), 0, 127]))); held.append(note)
        elif r < 0.52 and held: out.append("off %d" % krng.choice(held))
        elif r < 0.58: out.append("pedal %r" % krng.choice([0, 1, 0.5, krng.random()]))
        elif r < 0.63: out.append("mode " + krng.choice(["dyad", "mono", "poly", "poly"]))
        elif r < 0.67: out.append("layers " + krng.choice(["off", "split", "layer"]))
        elif r < 0.70: out.append("draw %d %s %s" % (krng.randint(0, 1), krng.choice([str(krng.randint(1, 9)), "%.3f" % krng.uniform(1, 9)]),
                                                     krng.choice(["outer", "lowest", "highest", "recent"])))
        elif r < 0.72: out.append("pair " + krng.choice(["each", "against"]))
        elif r < 0.74: out.append("just %d" % krng.randint(0, 1))
        elif r < 0.76: out.append("hold %d" % krng.randint(0, 1))
        elif r < 0.78: out.append("learn")
        elif r < 0.81: out.append("cc %d %d" % (krng.choice([16, 17, 42, 64, 7]), krng.randint(0, 127)))
        elif r < 0.83: out.append("gen mode " + krng.choice(["wave", "wave", "figure", "harmonograph", "wireframe"]))
        elif r < 0.85: out.append("drive %d" % krng.randint(0, 1))
        elif r < 0.87: out.append("play %d" % krng.randint(0, 1))
        elif r < 0.88: out.append("gen figure " + krng.choice(["Rose", "Circle"]))
        elif r < 0.89: out.append("panic")
        elif r < 0.91: out.append("bytes " + ",".join(str(krng.choice([0x90, 0x80, 0xB0, 0xF8, krng.randint(0, 127), krng.randint(0, 127)])) for _ in range(krng.randint(1, 7))))
        else: out.append("frame %d" % krng.choice([16, 16, 33, 0, 250]))
    return krun(*out)
kruns += [("random-%d" % i, kfuzz(80)) for i in range(40)]
# The arpeggiator (K5), on the clock: a chord struck over a few milliseconds
# and gathered, the steps every quaver from the first key, each pattern, the
# dyad's pairs, the tempo changed under it, switched off and on with keys down,
# the out it sends on, and a random walk from the seeded generator.
def steps(start, stop, every): return ["at %r" % t if i == 0 else "tick" for t in range(start, stop, every) for i in (0, 1)]
kruns += [
    ("arp-gather", krun("out 1", "arp up 1/8 1", "at 1000", "on 64 90", "at 1008", "on 60 100", "at 1012", "on 67 80",
                        "at 1020", "tick", *steps(1030, 2100, 20))),
    ("arp-patterns", krun("out 1", "arp down 1/8 2", "at 0", "on 60 100", "on 64 90", "on 67 80", *steps(30, 1700, 50),
                          "arp updown 1/16 1", *steps(1700, 3000, 40), "arp played 1/4 1", "on 62 70", *steps(3000, 5200, 100))),
    ("arp-dyad", krun("arp up 1/8 2", "at 0", "on 48 100", "on 55 90", "on 60 80", *steps(30, 1400, 25),
                      "mode mono", *steps(1400, 2000, 25), "mode poly", *steps(2000, 2600, 25))),
    ("arp-tempo", krun("arp up 1/16t 1", "at 0", "on 60 100", "on 63 90", "on 67 80", *steps(30, 600, 10), "bpm 90",
                       *steps(600, 1200, 10), "bpm 200", "arp up 1/4 3", *steps(1200, 2400, 30))),
    ("arp-switch", krun("out 1", "mode poly", "at 0", "on 60 100", "on 64 90", "on 67 80", "at 40", "arp up 1/8 1",
                        *steps(50, 600, 50), "arp off 1/8 1", "at 700", "tick", "arp up 1/8 1", *steps(700, 1300, 50),
                        "off 60", "off 64", "at 1400", "tick", "off 67", "at 1500", "tick", "on 72 60", *steps(1500, 2000, 50))),
    ("arp-random", krun("out 1", "arp random 1/16 2", "at 0", "on 57 100", "on 60 90", "on 64 80", "on 69 70",
                        *steps(30, 2000, 25))),
    ("arp-undriven", krun("arp up 1/8 1", "drive 0", "at 0", "on 60 100", "on 64 90", *steps(30, 600, 50), "drive 1",
                          *steps(600, 1200, 50), "arp nonsense 1/9 0", *steps(1200, 1500, 50))),
    # The keys come up while the kind takes no notes, so nothing tells the
    # arpeggiator; the kind changed back, the next frame finds it running with
    # nothing held, and stops it.
    ("arp-kind", krun("out 1", "arp up 1/8 1", "at 0", "on 60 100", "on 64 90", *steps(30, 400, 50), "gen mode wireframe",
                      "off 60", "off 64", "gen mode wave", "at 450", "tick", "at 500", "tick")),
    ("arp-pedal", krun("arp up 1/8 1", "pedal 1", "at 0", "on 60 100", "on 67 90", "off 60", *steps(30, 700, 50), "pedal 0",
                       *steps(700, 1200, 50), "off 67", "at 1300", "tick")),
]
def kafuzz(n):
    out, t, held = ["frame 16"], 0, []
    for _ in range(n):
        r = krng.random()
        t += krng.choice([0, 1, 5, 8, 16, 24, 26, 50, 125, 250, 400])
        out.append("at %d" % t)
        if r < 0.25:
            note = krng.choice([krng.randint(40, 80), krng.choice(held or [60])])
            out.append("on %d %d" % (note, krng.choice([krng.randint(1, 127), 127]))); held.append(note)
        elif r < 0.4 and held: out.append("off %d" % krng.choice(held))
        elif r < 0.55: out.append("tick")
        elif r < 0.62: out.append("arp %s %s %s" % (krng.choice(["up", "down", "updown", "played", "random", "off"]),
                                                    krng.choice(["1/4", "1/8", "1/16", "1/8t", "1/16t", "1/3"]),
                                                    krng.choice(["1", "2", "3", "0", "x"])))
        elif r < 0.66: out.append("bpm %r" % krng.choice([60, 90, 120, 133.3, 200]))
        elif r < 0.69: out.append("out %d" % krng.randint(0, 1))
        elif r < 0.73: out.append("mode " + krng.choice(["dyad", "mono", "poly"]))
        elif r < 0.75: out.append("pedal %r" % krng.choice([0, 1]))
        elif r < 0.77: out.append("layers " + krng.choice(["off", "split", "layer"]))
        elif r < 0.79: out.append("drive %d" % krng.randint(0, 1))
        elif r < 0.80: out.append("gen mode " + krng.choice(["wave", "figure", "wireframe"]))
        elif r < 0.81: out.append("panic")
        else: out.append("frame 16")
    return krun(*out)
kruns += [("arp-random-%d" % i, kafuzz(120)) for i in range(40)]

ktext = "".join(t for _, t in kruns)
kjs, kcpp = kboth(ktext, "keyboard.txt")
klines = [len(t.strip().split("\n")) - 2 for _, t in kruns]
def kslice(out, i):
    lines = out.strip().split("\n")
    start = sum(klines[:i])
    return "\n".join(lines[start:start + klines[i]])
for i, (name, _) in enumerate(kruns):
    if name.startswith("random-"): continue
    d = kdiff(kslice(kjs, i), kslice(kcpp, i))
    check("%s: %d commands, every call the same" % (name, klines[i]), d is None, d or "")
rbad = [n for i, (n, _) in enumerate(kruns) if n.startswith("random-") and kdiff(kslice(kjs, i), kslice(kcpp, i))]
check("40 random sequences of 80 commands, every call the same", not rbad, ", ".join(rbad))

# Each run has to show what it is for, or agreeing on it proves nothing.
def kout(name): return kslice(kjs, next(i for i, (n, _) in enumerate(kruns) if n == name))
check("the dyad sets an interval wider than an octave, and clamps the pitch at both ends",
      "set octaves 2." in kout("dyad") and "set freq 4000.0" in kout("dyad-edges") and "set freq 30.00" in kout("dyad-edges"))
check("a chord leaves notes heard and not drawn, by every rule",
      all(r in kout("poly-rules") for r in ("/u+", "/x+", "/y")) and "/xy " in kout("poly-one"))
check("past eight held notes the oldest stops sounding", "poly 8 2 11" in kout("poly-many"))
check("split, layer B plays its own notes and each layer counts its own strikes",
      re.search(r"set voices \S+ 1 ", kout("split")) and re.search(r"strikes (\d+) (?!\1)\d+ ", kout("split")))
check("against, each layer's drawn notes go on one axis", "layout against" in kout("split")
      and re.search(r"set voices [^ ]*/y[^ ]* 1", kout("split")))
check("the pedal holds released keys, and lets them go", "sustained 60" in kout("pedal")
      and "sustained 60+64" in kout("pedal"))
check("bytes: running status, a clock tick inside a note, and the realtime handed on",
      "realtime 248" in kout("bytes") and "notes 64/" in kout("bytes"))
check("a played rose takes the dyad's ratio as its petals", "set detail 1.5" in kout("figure"))
check("the pitched harmonograph is pitched, and a key strikes it", "set pitched 1" in kout("harmonograph")
      and ":: reswing" in kout("harmonograph"))
check("a controller walks towards where it was moved", "16/Drawbar_1/64/0.0000" in kout("controllers")
      and "16/Drawbar_1/64/0.1428" in kout("controllers"))
rnd = "\n".join(kslice(kjs, i) for i, (n, _) in enumerate(kruns) if n.startswith("random-"))
check("the random sequences reach chords, layers, the pedal and the drawings",
      all(w in rnd for w in ("set voices", " 1 | ", "layout each", "sustained 6", "set figureRate", "set pitched 1")))

# Nulls: the page told something different, and the port must disagree.
def knull(name, old, new, what):
    text = dict(kruns)[name]
    assert old in text, old
    js, _ = kboth(text.replace(old, new, 1))
    i = next(k for k, (n, _) in enumerate(kruns) if n == name)
    check("and against " + what, kdiff(js, kslice(kcpp, i)) is not None)
# The arpeggiator's steps, read from the page's lines: when each landed (the
# last `at` before it), the mode, what the generator was shown, and what went out.
def arpsteps(name):
    text = dict(kruns)[name].strip().split("\n")[1:-1]
    out, t, last = [], 0.0, 0
    for cmd, line in zip(text, kout(name).strip().split("\n")):
        if cmd.startswith("at "): t = float(cmd.split()[1])
        tail = line.split(" arp ")[-1].split()
        n = int(float(tail[3]))
        if n > last:
            cur = [int(c.split("/")[0]) for c in tail[4].split("+")] if tail[4] != "-" else []
            out.append({"t": t, "mode": tail[0], "current": cur, "sent": tail[5], "calls": line.split(" | ")[0]})
        last = n
    return out
A = arpsteps("arp-gather")
# When the first step went out, from the out's own log: the timer's time, not the frame's.
first_out = float(re.search(r"out 60 \S+ (\S+)", A[0]["calls"]).group(1))
check("a chord struck over 12 ms is gathered: the first step is its lowest note, 25 ms after the first key, not the key that came first",
      first_out == 1025 and A[0]["current"] == [60], "%s %s" % (first_out, A[0]["current"]))
check("and each step after it falls on the first frame after its quaver is due, counted from the first key so it cannot drift",
      len(A) >= 4 and all(0 <= st["t"] - (1025 + 250 * k) < 20 for k, st in enumerate(A)), str([st["t"] for st in A]))
check("in the dyad each step pairs the lowest held note with the arpeggio's, and each is struck: the gate closes and opens",
      [st["current"] for st in A[:4]] == [[60], [60, 64], [60, 67], [60]]
      and all(st["calls"].index("gate 0") < st["calls"].index("gate 1") for st in A[:4]),
      str([st["current"] for st in A[:4]]))
check("each step's note goes out, and the one before is let go",
      [st["sent"] for st in A[:4]] == ["60", "64", "67", "60"] and "outoff 60" in A[1]["calls"], str([st["sent"] for st in A[:4]]))
P = arpsteps("arp-patterns")
picks = lambda mode: [st["current"][-1] for st in P if st["mode"] == mode]
check("down plays the top first through two octaves, up-and-down turns without repeating its ends, played keeps the order the keys came",
      picks("down")[:6] == [79, 76, 72, 67, 64, 60] and picks("updown")[:6] == [60, 64, 67, 64, 60, 64]
      and picks("played")[:4] == [60, 64, 67, 62],
      "%s / %s / %s" % (picks("down")[:6], picks("updown")[:6], picks("played")[:5]))
D = arpsteps("arp-dyad")
check("mono and poly play the arpeggio's note alone; only the dyad pairs it",
      all(len(st["current"]) == 1 for st in D if st["mode"] == "up" and st["t"] >= 1400)
      and any(len(st["current"]) == 2 for st in D if st["t"] < 1400), str([st["current"] for st in D][-6:]))
T = arpsteps("arp-tempo")
gap = lambda lo, hi: [b["t"] - a["t"] for a, b in zip(T, T[1:]) if lo <= a["t"] and b["t"] < hi]
check("the step is the rate at the tempo in force: a sixteenth triplet at 120 is 83 ms, at 90 is 111",
      all(80 <= g <= 90 for g in gap(30, 600)) and all(110 <= g <= 120 for g in gap(640, 1200)),
      "%s | %s" % (gap(30, 600)[:4], gap(640, 1200)[:4]))
S = kout("arp-switch").strip().split("\n")
off_line = next(l for l in S if l.startswith("arp") and " arp off " in l)
check("switched off with keys down, the generator is given the whole of what is held at once, and the out lets go",
      "outoff 64" in off_line and off_line.count("/") > 6 and "set voices 60/" in off_line and "64/" in off_line.split("set voices")[1],
      off_line[:160])
last_off = next(l for l in S if l.startswith("off") and " - 3 - -" in l.split(" arp ")[-1])
check("letting go of the last key stops it: the generator is told nothing is held, and the last note out is let go",
      "outoff 67" in last_off and "gate 0" in last_off, last_off[:120])
K = kout("arp-kind").strip().split("\n")
check("a running arpeggio that finds nothing held at its next frame stops, and lets its last note go",
      "outoff 64" in K[-3] and " - " in K[-3].split(" arp ")[-1] and "gate 0" in K[-3], K[-3][:120])
U = arpsteps("arp-undriven")
check("with notes not driving the generator it does not step, and driven again it starts",
      all(st["t"] >= 600 for st in U) and len(U) >= 2, str([st["t"] for st in U][:4]))
R = arpsteps("arp-random")
check("a random walk picks only what is held, and is not the order up",
      set(st["current"][-1] for st in R) <= {57, 60, 64, 69, 72, 76, 81} and len(set(st["current"][-1] for st in R)) >= 5
      and [st["current"][-1] for st in R[:4]] != [57, 60, 64, 69], str([st["current"][-1] for st in R[:8]]))
knull("arp-gather", "at 1008", "at 1030", "the second key landing after the chord was gathered")
knull("arp-tempo", "bpm 90", "bpm 91", "a tempo a beat a minute faster under the arpeggio")
knull("arp-patterns", "arp down 1/8 2", "arp up 1/8 2", "up where it said down")
knull("poly-outer", "on 67 80", "on 67 81", "a chord with one velocity a step harder")
knull("split", "layers split", "layers layer", "a layer where there was a split")
knull("pedal", "pedal 1", "pedal 0.4", "a pedal not quite down")
knull("bytes", "0x90,72,0xF8,77", "0x90,72,77,0xF8", "a clock tick after the velocity instead of inside it")
knull("figure", "panel figureRate 120", "panel figureRate 121", "a trace-rate slider a hertz on")
knull("dyad-hold", "hold 1", "hold 0", "Hold left off")
check("and the comparison fails against the page's lines one command out of step",
      kdiff("\n".join(kjs.strip().split("\n")[1:]), "\n".join(kcpp.strip().split("\n")[:-1])) is not None)

print("\n--- the matrix ---")
# The page's routings, fades, events and routes, lifted by name, and
# scope::Matrix, through the same commands. A line a command: the events
# fired and the picture's offsets written, the routes the generator is given
# each frame, the stored depths, and how much is heard and fading.
mexe = build("matrix_cpp")
def mboth(text, name="matrix_one.txt"):
    path = os.path.join(BUILD, name)
    with open(path, "w") as f: f.write(text)
    js = subprocess.run(["node", os.path.join(HERE, "tools", "matrix_js.mjs"), path], check=True,
                        capture_output=True, text=True).stdout
    return js, subprocess.run([mexe, path], check=True, capture_output=True, text=True).stdout

# The sources every run has: an LFO the loop reads for itself, a held level,
# a stepped key, two picture sources with a reach, one whose reach varies,
# and two event sources, one from the picture.
MSETUP = ["source lfo1 index=0", "source lfo2 index=1", "source level", "source key stepped", "source pedal stepped",
          "source photo picture reach=0.5", "source shape picture reach=0.5", "source hear reach=0.5 varies",
          "source onset event", "source pic.hit event picture", "visual view.rotate 1 -2 2 0.25",
          "visual view.zoom 8 0 24 20", "event gen.kick", "event gen.pluck",
          "value level 0.6", "value photo 0.7", "value shape 0.9", "value hear 0.8", "value lfo1 0.3"]
def mrun(*commands): return "run\n%s\nend\n" % "\n".join(MSETUP + list(commands))
def frames(start, stop, step): return ["at %d" % t if i % 2 == 0 else "frame" for t in range(start, stop, step) for i in (0, 1)]

mruns = [
    ("routes", mrun("dests", "at 0", "frame", "route lfo1 gen.freq 0.4", "route level gen.amp 0.8", "route level gen.bar3 -0.5",
                    "route lfo2 gen.spinZ 1", "route nobody gen.freq 1", "route level gen.nowhere 1",
                    "route onset gen.freq 1", "route level gen.kick 1", "frame", "value level 0.25", "frame",
                    "amount level gen.amp 0", "frame", "encode")),
    ("reach", mrun("source pvary picture reach=0.3 varies", "value pvary 0.5", "route pvary gen.twist 0.9",
                   "route photo gen.freq 0.9", "route shape gen.freq -0.8", "route hear gen.fm 0.9",
                   "route photo gen.amp 0.7", "route shape gen.amp 0.4", "frame", "value photo 1", "value shape -1",
                   "frame", "amount hear gen.fm -2", "amount photo gen.freq 0.2", "frame", "encode")),
    ("visual", mrun("route level view.rotate 1", "route photo view.rotate 0.5", "route shape view.rotate 0.5",
                    "frame", "value level 2.5", "frame", "route level view.zoom 1", "frame", "value level -9", "frame",
                    "route hear view.zoom -0.9", "frame", "visual view.rotate 1 -2 2 -0.5", "frame")),
    ("events", mrun("route onset gen.kick 0.6", "route pic.hit gen.kick 1", "route onset gen.pluck 0", "frame",
                    "count onset 1", "frame", "frame", "count onset 3", "frame", "amount onset gen.kick -0.3",
                    "count onset 4", "frame", "count pic.hit 2", "frame", "load onset>gen.kick@0.9", "count onset 5",
                    "frame", "count onset 6", "frame", "route onset gen.pluck 0.5", "count onset 7", "frame")),
    ("forget", mrun("route level gen.freq 0.5", "route photo gen.twist 0.3", "frame", "forget level", "frame",
                    "source level", "frame", "forget photo", "frame")),
    ("fade-in", mrun("fade in 1", "at 0", "frame", "route level gen.freq 0.8", "route lfo1 gen.amp 0.5", "routes",
                     *frames(100, 1300, 100), "unroute level gen.freq", "at 1400", "frame")),
    ("fade-out", mrun("route level gen.freq 0.8", "route photo gen.freq 0.4", "route level view.rotate 1", "fade out 0.5",
                      "at 0", "frame", "unroute level gen.freq", "unroute level view.rotate", *frames(50, 700, 50),
                      "unroute photo gen.freq", *frames(700, 1300, 100))),
    ("fade-both", mrun("fade both 2", "env 0 attackMid=0.2 releaseMid=0.8", "at 0", "route level gen.freq 0.8", "frame",
                       *frames(250, 1000, 250), "unroute level gen.freq", *frames(1000, 2000, 250),
                       "route level gen.freq 0.8", *frames(2000, 5000, 500))),
    ("preset", mrun("route level gen.freq 0.8", "route lfo1 gen.amp 0.5", "fade both 1", "at 0", "frame",
                    "load level>gen.freq@0.6;photo>gen.twist@0.4", "at 10", "frame", *frames(200, 1400, 300),
                    "fade off", "frame", "fade in", "frame")),
    ("stepped", mrun("fade both 1", "env 0 delay=0.2 attack=0.5 decay=0.4 sustain=0.6 release=0.8",
                     "route key gen.fm 1", "route pedal view.rotate 1", "at 0", "frame", "value key 0.7", "at 10",
                     "frame", *frames(100, 1400, 150), "value key 0.9", *frames(1400, 2000, 150), "value key 0.4",
                     *frames(2000, 2600, 150), "value key -0.8", *frames(2600, 3200, 150), "value key -0.3",
                     *frames(3200, 3800, 150), "value key 0", *frames(2600, 3800, 200), "value pedal 1",
                     *frames(3800, 4200, 100))),
    ("stepped-loop", mrun("fade in 1", "env 0 attack=0.3 decay=0.2 sustain=0.5 loop=true", "route key gen.fm 1",
                          "at 0", "frame", "value key 1", *frames(10, 2000, 70), "fade out", "frame", "value key 0",
                          *frames(2000, 2600, 100))),
    ("layered", mrun("fade both 1", "env 1 attack=0.2 decay=0.3 sustain=0.5 release=3 attackMid=0.7 restart=true",
                     "env 0 restart=false", "layers 1", "route key gen.fm 1", "route level gen.freq 0.5", "at 0",
                     "frame", "value key 0.8", *frames(50, 600, 50), "strike 1", *frames(600, 900, 50), "strike 0",
                     *frames(900, 1200, 100), "layers 0", "frame", "layers 1", "unroute level gen.freq",
                     *frames(1200, 2000, 200))),
    ("envelope", mrun("env 0 attack=99 release=0 delay=-1 sustain=-1 attackMid=0 decayMid=1 releaseMid=0.5",
                      "fade both", "fade sideways 2", "route key gen.fm 1", "at 0", "frame",
                      "value key 1", *frames(10, 12000, 499), "value key 0", *frames(12000, 12500, 99))),
    ("envelope-late", mrun("env 0 delay=7 attack=0.1 decay=0.1 sustain=0.5", "fade in", "route key gen.fm 1", "at 0",
                           "frame", "value key 1", "at 10", "frame", *frames(4000, 8000, 500))),
    ("envelope-seconds", mrun("env 0 seconds=3 attack=1", "fade both", "route key gen.fm 1", "at 0", "frame",
                              "value key 1", "at 10", "frame", *frames(300, 3500, 300), "value key 0",
                              *frames(3500, 7000, 500))),
    ("envelope-names", mrun("env 0 seconds=3 attack=1", "env 0 inSeconds=4 attack=0.7",
                            "env 0 outSeconds=0.3 outMid=0.3 inMid=0.6 releaseMid=0.8", "env 1 inSeconds=0.4 outMid=0.2",
                            "layers 1", "fade both", "route key gen.fm 1", "at 0", "frame", "value key 1",
                            *frames(10, 1000, 99), "value key 0", *frames(1000, 1500, 49))),
    ("envelope-unreadable", mrun("env 0 attack=abc delay=abc sustain=abc", "fade in", "route key gen.fm 1", "at 0",
                                 "frame", "value key 1", *frames(100, 2500, 300))),
    ("strikes-first", mrun("fade both 1", "env 0 restart=true attack=0.2 decay=0.2 sustain=0.5 delay=0.2",
                           "strike 0", "strike 0", "value key 1", "route key gen.fm 1", "at 0", "frame",
                           *frames(50, 900, 50), "strike 0", *frames(900, 1500, 50))),
    # The page in the plugin sends its whole list after each edit. A pair kept
    # is the same routing, so an event on it fires on the next new count; the
    # same list loaded as a preset is new routings, which never fire on the
    # count they find. A depth carried at full precision, and one past a
    # reach held to it as the page holds it.
    ("edit", mrun("route onset gen.kick 0.6", "route level gen.freq 0.5", "fade both 1", "at 0", "frame", "count onset 1",
                  "frame", "edit onset>gen.kick@0.7;level>gen.freq@0.123456789012345;photo>gen.twist@0.4", "count onset 2",
                  "at 50", "frame", "load onset>gen.kick@0.7;level>gen.freq@0.123456789012345;photo>gen.twist@0.4",
                  "count onset 3", "at 100", "frame", "count onset 4", "edit level>gen.freq@0.5", "at 150", "frame",
                  "edit onset>gen.kick@0.2;level>gen.freq@0.5", "count onset 5", "at 200", "frame", "count onset 6",
                  "at 250", "frame", "edit level>gen.freq@0.5;photo>gen.freq@0.9", "routes", *frames(300, 1500, 200),
                  "encode")),
    # A depth changed and the routing taken off before the next frame: what
    # fades out is the new depth, since the page's fade holds the routing
    # itself. Found by the edits' fuzz; the port's fade held a stale copy.
    ("fade-depth", mrun("route level gen.freq 0.8", "fade out 1", "at 0", "frame", "amount level gen.freq 0.3",
                        "unroute level gen.freq", *frames(50, 1200, 100))),
    ("codes", mrun("load a>b@1;;x>y@1.2.3;level>gen.freq@-0.0625;bad;@;c>d@;e>f@.5;g>h>i@0.1875;j@k>l@1;m>n@-.25;o>p@5.;q>r@-",
                   "encode", "frame", "load level>gen.amp@0.0005;level>gen.fm@1.9995;level>gen.freq@-0.00049;p0>q0@-0;p9>q9@9.9996;pm>qm@-99.9999", "encode",
                   "load", "encode")),
]

mrng = random.Random(96)
MSRC = ["lfo1", "lfo2", "level", "key", "pedal", "photo", "shape", "hear", "onset", "pic.hit", "ghost"]
MDST = ["gen.freq", "gen.amp", "gen.fm", "gen.bar2", "gen.twist", "view.rotate", "view.zoom", "gen.kick", "gen.pluck"]
def mfuzz(n):
    out, t = ["at 0"], 0
    for _ in range(n):
        r = mrng.random()
        if r < 0.18: out.append("route %s %s %r" % (mrng.choice(MSRC), mrng.choice(MDST), round(mrng.uniform(-1.2, 1.2), 3)))
        elif r < 0.25: out.append("unroute %s %s" % (mrng.choice(MSRC), mrng.choice(MDST)))
        elif r < 0.30: out.append("amount %s %s %r" % (mrng.choice(MSRC), mrng.choice(MDST), round(mrng.uniform(-1, 1), 2)))
        elif r < 0.42: out.append("value %s %r" % (mrng.choice(MSRC), mrng.choice([0, 0, 1, round(mrng.uniform(-1, 1), 3)])))
        elif r < 0.47: out.append("count %s %d" % (mrng.choice(["onset", "pic.hit"]), mrng.randint(0, 9)))
        elif r < 0.51: out.append("fade %s %s" % (mrng.choice(["off", "in", "out", "both", "both"]), mrng.choice(["", "0.3", "1"])))
        elif r < 0.55: out.append("env %d %s=%r" % (mrng.randint(0, 1), mrng.choice(["attack", "release", "decay", "delay", "sustain", "attackMid", "releaseMid"]), round(mrng.uniform(0, 1.5), 2)))
        elif r < 0.57: out.append("env %d %s=%s" % (mrng.randint(0, 1), mrng.choice(["loop", "restart"]), mrng.choice(["true", "false"])))
        elif r < 0.60: out.append("layers %d" % mrng.randint(0, 1))
        elif r < 0.63: out.append("strike %d" % mrng.randint(0, 1))
        elif r < 0.65: out.append("load " + ";".join("%s>%s@%.3f" % (mrng.choice(MSRC), mrng.choice(MDST), mrng.uniform(-1, 1)) for _ in range(mrng.randint(0, 4))))
        elif r < 0.66: out.append("forget " + mrng.choice(["level", "photo", "onset"]))
        # Never a pair twice: the page's list cannot hold one twice.
        elif r < 0.70: out.append("edit " + ";".join("%s>%s@%r" % (src, dst, mrng.uniform(-1, 1)) for src, dst in mrng.sample(
            [(src, dst) for src in ("level", "onset", "photo") for dst in ("gen.freq", "gen.kick", "view.rotate")], mrng.randint(0, 3))))
        else:
            t += mrng.choice([16, 16, 33, 100, 400, 0])
            out += ["at %d" % t, "frame"]
    return mrun(*out)
mruns += [("random-%d" % i, mfuzz(120)) for i in range(40)]

mtext = "".join(t for _, t in mruns)
mjs, mcpp = mboth(mtext, "matrix.txt")
mlines = [len(t.strip().split("\n")) - 2 for _, t in mruns]
def mslice(out, i):
    lines = out.strip().split("\n")
    start = sum(mlines[:i])
    return "\n".join(lines[start:start + mlines[i]])
for i, (name, _) in enumerate(mruns):
    if name.startswith("random-"): continue
    d = kdiff(mslice(mjs, i), mslice(mcpp, i))
    check("%s: %d commands, the same routes, events and offsets" % (name, mlines[i]), d is None, d or "")
rbad = [n for i, (n, _) in enumerate(mruns) if n.startswith("random-") and kdiff(mslice(mjs, i), mslice(mcpp, i))]
check("40 random sequences of 120 commands, the same routes, events and offsets", not rbad, ", ".join(rbad))
def mout(name): return mslice(mjs, next(i for i, (n, _) in enumerate(mruns) if n == name))
def frame_lines(name): return [l for l in mout(name).split("\n") if l.startswith("frame")]
def route_amounts(line):
    m = re.search(r"routes (\S+)", line)
    return [] if not m or m.group(1) == "-" else [float(r.split("/")[4]) for r in m.group(1).split("+")]
check("the generator's destinations are the page's, each on its slot", "gen.spinZ/31/0" in mout("routes")
      and "gen.amp/1/1" in mout("routes") and mout("routes").count("/0+") >= 30)
fi = [route_amounts(l) for l in frame_lines("fade-in")]
check("a routing fades in: part-way at first, whole by the end of its time",
      any(0.05 < a[0] < 0.75 for a in fi if a) and any(abs(a[0] - 0.8) < 1e-12 for a in fi if a))
fo = frame_lines("fade-out")
check("a routing taken off is heard fading, then forgotten", "heard 3" in "\n".join(fo) and fo[-1].split("heard ")[1].startswith("0"))
check("the loop's total into one slot is held to a half", "/1.0000000000000000/1.0000000000000000/0" in mout("reach")
      and "u/0.50000000000000000/" in mout("reach"))
check("events fire on a new count only, never on the count found, and never at no depth",
      mout("events").count(":: fire gen.kick") == 5 and "fire gen.pluck" not in mout("events")
      and ":: fire gen.kick -0.29" in mout("events"))
check("the picture's offsets are held to their ranges", "visual view.rotate 1.75" in mout("visual")
      and "visual view.zoom -20" in mout("visual"))
st = "\n".join(frame_lines("stepped"))
check("a stepped source waits out its delay, rises, settles to its sustain and falls",
      "/0.69999999999999996/" not in st.split("\n")[2] and "0.41999999999999998/" in st and " :: visual view.rotate" in st)
check("layered, layer B's depths and envelope are its own", any(
      len(set(l.split("routes ")[1].split(" ")[0].split("/")[1:3])) == 2 for l in frame_lines("layered") if "routes u/" in l))
# The pair in both the old preset and the new keeps its gain: at 0.6 from the
# first frame after the load, never below. All of an empty list is true, so
# the frames have to be there.
after = [route_amounts(l) for l in frame_lines("preset")[1:]]
check("a preset's pair already playing does not dip", len(after) >= 5 and all(a and abs(a[0] - 0.6) < 1e-12 for a in after))
fd = [route_amounts(l) for l in frame_lines("fade-depth")[1:]]
check("a depth changed just before its routing goes is the depth that fades out",
      len(fd) > 5 and all(abs(x) <= 0.3 + 1e-12 for a in fd for x in a) and any(x > 0.25 for a in fd for x in a),
      repr(fd[:3]))
ed = mout("edit")
check("an edit keeps the routings it kept: an event on one fires on the next count, and not after a load of the same list",
      ed.count(":: fire gen.kick") == 3 and ":: fire gen.kick 0.69999999999999996" in ed
      and ":: fire gen.kick 0.20000000000000001" in ed, "%d fired" % ed.count(":: fire gen.kick"))
check("an edit's depth arrives whole, and one past its reach is held to it",
      "amounts 0.69999999999999996+0.12345678901234500+" in ed and "photo>gen.freq@0.500" in ed)
check("codes: the page's own rounding, and the malformed parts skipped",
      "level>gen.freq@-0.063" in mout("codes") and "g>h>i@0.188" in mout("codes") and "m>n@-0.250" in mout("codes")
      and "bad" not in mout("codes") and "c>d" not in mout("codes") and "j@k>l@1.000" in mout("codes")
      and "x>y@NaN" in mout("codes") and "p0>q0@0.000;p9>q9@10.000;pm>qm@-100.000" in mout("codes"))
rnd = "\n".join(mslice(mjs, i) for i, (n, _) in enumerate(mruns) if n.startswith("random-"))
check("the random sequences reach fades, ghosts, events and the loop", all(w in rnd for w in (":: fire", "gains 1", ":: visual", "routes u/")))

def mnull(name, old, new, what):
    text = dict(mruns)[name]
    assert old in text, old
    js, _ = mboth(text.replace(old, new, 1))
    i = next(k for k, (n, _) in enumerate(mruns) if n == name)
    check("and against " + what, kdiff(js, mslice(mcpp, i)) is not None)
mnull("fade-in", "fade in 1", "fade in 1.1", "a fade a tenth of a second longer")
mnull("stepped", "sustain=0.6", "sustain=0.61", "a sustain a hundredth higher")
mnull("reach", "source photo picture reach=0.5", "source photo picture reach=0.51", "a reach a hundredth further")
mnull("events", "count onset 3", "count onset 1", "a count that did not move")
mnull("layered", "strike 1", "strike 0", "the other layer struck")
mnull("edit", "edit onset>gen.kick@0.7;", "load onset>gen.kick@0.7;", "the edit sent as a preset")
check("and the comparison fails against the page's lines one command out of step",
      kdiff("\n".join(mjs.strip().split("\n")[1:]), "\n".join(mcpp.strip().split("\n")[:-1])) is not None)

print("\n--- setup codes ---")
# The page's DEFAULTS, encodeSetup, decodeSetup and migrateSetup, lifted by
# name and run in strict mode, against scope/setup.h: a line a command, the
# code or the setup read back, compared character for character.
import json as _json, base64
sexe = build("setup_cpp")
def sboth(lines, name="setup_one.txt"):
    path = os.path.join(BUILD, name)
    with open(path, "w", encoding="utf-8") as f: f.write("\n".join(lines) + "\n")
    js = subprocess.run(["node", os.path.join(HERE, "tools", "setup_js.mjs"), path], check=True,
                        capture_output=True, text=True).stdout.split("\n")
    return js, subprocess.run([sexe, path], check=True, capture_output=True, text=True).stdout.split("\n")

srng = random.Random(97)
DEFAULT_KEYS = ["gen", "shape", "freq", "amp", "interval", "just", "phase", "figure", "detail", "figText", "mod", "bars",
                "midiMode", "layers", "splitAt", "planeLimit", "delayMs", "oscFm", "vcfCut", "c0s", "c1s", "level", "trig"]
NUMBERS = [0, -0.0, 1, -1, 0.1, 0.5, 1/3, 2/3, 123.456, 1e-6, 1e-7, 1.5e-7, 9.99e-7, 123456789012345680000.0, 1e21, 1.5e21,
           1e300, 5e-324, 1.7976931348623157e308, 2**53, 2**53 + 2, 0.1 + 0.2, -1e-7, 100, 1000000, 4.35, 220.0]
STRINGS = ["", "plain", "quote\"back\\slash", "tab\tnew\nline\rcr\bfeed\f", "ctl\u0001\u001f\u007f", "caf\u00e9 \u00ff",
           "\u00a0nbsp", "lfo1>gen.freq@0.400;lfo2>gen.amp@-0.250", "slash/ok", "\u2028line", "\u4e2d\u6587",
           "\U0001F3B5", "lone \ud800 high", "lone \udc00 low"]
def rvalue(depth=0):
    r = srng.random()
    if r < 0.45: return srng.choice(NUMBERS + [srng.uniform(-1e4, 1e4), srng.randint(-1000, 1000), srng.random() * 10 ** srng.randint(-9, 25)])
    if r < 0.7: return srng.choice(STRINGS)
    if r < 0.85: return srng.choice([True, False])
    if r < 0.9: return None
    if depth < 2 and r < 0.95: return [rvalue(depth + 1) for _ in range(srng.randint(0, 3))]
    if depth < 2: return {srng.choice(["a", "0", "7", "b"]): rvalue(depth + 1) for _ in range(srng.randint(0, 3))}
    return 1
def dumps(obj):
    # Escaped, so a lone surrogate survives the file; the runs below also
    # carry characters past ASCII as they are.
    return _json.dumps(obj, ensure_ascii=True, separators=(",", ":"))
def snapshot():
    snap = {}
    for k in srng.sample(DEFAULT_KEYS, srng.randint(0, len(DEFAULT_KEYS))): snap[k] = rvalue()
    for _ in range(srng.randint(0, 3)): snap[srng.choice(["extra", "0", "12", "007", "4294967294", "4294967295", "v"])] = rvalue()
    return snap
def old_setup():
    st = {}
    if srng.random() < 0.8: st["v"] = srng.choice([1, 2, 3, 4, 5, "2", "x", None, [3], 1.5, True])
    if srng.random() < 0.7: st["trig"] = srng.choice([0, 1, 2, "1", "x", [1], [], None, True, 0.5, -1, {"a": 1}])
    for key in ("c0s", "c1s", "c2s"):
        if srng.random() < 0.6: st[key] = srng.choice([0, 3, 8, 9, -1, "3", " 3", "03", 3.0, 2.5, "length", True, None, [5], -0.0])
    if srng.random() < 0.7: st["level"] = srng.choice([100, -500, 1000, 999.5, 0.5, "250", "0x10", " 12 ", "1e2", "abc", None, True, [40], "", "Infinity"])
    if srng.random() < 0.4: st["planeClip"] = srng.choice([True, False, 1, "true", None])
    if srng.random() < 0.3: st["planeLimit"] = srng.choice([0, 2])
    for _ in range(srng.randint(0, 2)): st[srng.choice(["gen", "freq", "mod", "5"])] = rvalue()
    return st
def code_of(text):
    raw = text.encode("latin-1") if all(ord(c) < 256 for c in text) else text.encode("utf-8")
    return base64.b64encode(raw).decode()
def mangle(code):
    r = srng.random()
    if r < 0.5: return code.rstrip("=")
    if r < 0.6: return " \t" + code + "\t "
    if r < 0.7: return code[:len(code) // 2] + " " + code[len(code) // 2:]
    if r < 0.75: return code + "="
    if r < 0.8: return code[:-1] if len(code) % 4 == 2 else code + "A"
    if r < 0.85: return code.replace("A", "*", 1)
    if r < 0.9: return code.rstrip("=") + "=" * srng.randint(1, 3)
    return code
scmds = ["defaults"]
scmds += ["encode " + dumps(snapshot()) for _ in range(300)]
scmds += ["encode {\"figText\":\"caf\u00e9 \u00ff\",\"gen\":\"figure\"}", "encode {\"figText\":\"\u4e2d\"}",
          "encode {\"figText\":\"\U0001F3B5\"}", "encode {\"figText\":\"\u0100\"}", "encode {\"figText\":\"\u00ff\"}", "encode {}", "encode []", "encode 5", "encode {\"a\":1,\"a\":2,\"0\":3}", "encode {bad"]
for _ in range(400):
    text = _json.dumps(old_setup(), separators=(",", ":"))
    scmds.append("decode " + mangle(code_of(text)))
for text in ["5", "\"abc\"", "true", "false", "null", "0", "\"\"", "[1,2]", "-0", "{\"v\":\"4\"}", "{\"v\":4,\"level\":5}",
             "{bad json}", "{\"x\":\"caf\u00e9\"}", "{\"x\":\"\\ud800\"}", "  {\"trig\":1,\"c1s\":3,\"level\":64}  ", "{\"9\":1,\"1\":2,\"b\":3,\"a\":4,\"1\":5}"]:
    scmds.append("decode " + code_of(text))
# An old code on the -40 dB detent has a gain of exactly a hundred, so its
# level is read as a number and every rule of that reading shows: halves
# both ways, the infinities, hex, octal and binary, the forms that are not
# numbers, an array as its joined text, and nothing at all.
for level in ['"250"', '" 12 "', '"\\u00a0 7 \\u3000"', '"1e2"', '"abc"', '""', '"Infinity"', '"+Infinity"', '"-Infinity"',
              '"0x1F"', '"0X1f"', '"0b101"', '"0b102"', '"0o17"', '"0o8"', '"0x"', '"1e"', '"1e+"', '".5"', '"5."', '"."', '"+.5e-1"',
              '"12x"', '"1_0"', '"-"', '"+-1"', '"0x-1"', '"--1"', '"1e1000"', '[null]', '[1,null]', '[[2]]', '["3"]', '[1,2]', '{}',
              '0.125', '-0.125', '0.135', '-0.135', '10.005', '-0', 'null', 'true', 'false', '1e999']:
    scmds.append("decode " + code_of('{"v":1,"trig":0,"c0s":7,"level":%s}' % level))
for text in ['{"a":01}', '{"a":1.}', '{"a":-}', '{"a":1e}', '{"a":"x\\/y"}', '{"a":"\u0001"}', '{"a":1}\u00a0', '\u00a0{"a":1}',
             '{"a":1} x', '{"a":1e999,"b":-1e999}', '{"a":"\\ud83c\\udfb5"}', '{"a":"\\udfb5\\ud83c"}', '{"a":"\\ud83cx"}',
             '{"a":"\\u00e9\\u0000\\u001f"}', '{"a":"\\x41"}', '{"a":[1,]}', '{"a":1,}', '{"a" :1 , "b":[ ] }', '[01]',
             '{"a":"tab\there"}', '{"a":1E3,"b":1e-3,"c":-0.0}']:
    scmds.append("decode " + code_of(text))
for raw in ['{"v":4,"gen":"figure"}', '{"v":2,"trig":1,"c1s":"5","level":7}']:
    c = code_of(raw)
    scmds += ["decode " + c[:4] + "\t" + c[4:], "decode " + c[:4] + "\f" + c[4:8] + "\r\u000b" + c[8:]]
scmds += ['encode {"freq":330,"gen":"figure"}', "decode " + code_of('{"v":1,"trig":1,"c1s":3,"level":100}')]
scmds += ["decode ", "decode A", "decode AB==AB", "decode @@@@", "decode " + code_of("{}")[:-1] + "\u00a0"]
sjs, scpp = sboth(scmds, "setup.txt")
bad = [i for i, (a, b) in enumerate(zip(sjs, scpp)) if a != b]
check("the page's defaults, key for key and value for value", sjs[0] == scpp[0] and sjs[0].count(":") > 180)
enc = [i for i, c in enumerate(scmds) if c.startswith("encode")]
dec = [i for i, c in enumerate(scmds) if c.startswith("decode")]
check("%d snapshots encode to the page's code, character for character" % len(enc),
      len(sjs) == len(scpp) and not [i for i in bad if i in enc], (scmds[bad[0]][:120] + " | " + sjs[bad[0]][:100] + " | " + scpp[bad[0]][:100]) if bad else "")
check("%d codes decode and migrate to the page's setup, or fail as it fails" % len(dec),
      len(sjs) == len(scpp) and not [i for i in bad if i in dec])
# Each kind of case has to be there, or agreeing on it proves nothing.
sj = "\n".join(sjs)
check("the runs reach codes that throw, codes that do not read, migrated levels and the clip",
      sjs.count("throws") >= 3 and sjs.count("unreadable") >= 10 and '"planeLimit":1' in sj
      and re.search(r'"level":-?\d+', sj) and "1e+21" in sj and "1e-7" in sj and "\\ud800" in sj and "{u+d83c}{u+dfb5}" in sj)
check("codes with integer keys keep V8's order", any(l.startswith('read {"1":5,"9":1,"b":3,"a":4') for l in sjs))
# Nulls: the page told something else, and the port must disagree.
def snull(what, before, after):
    i = scmds.index(before)
    js, _ = sboth([scmds[i].replace(before, after, 1)])
    check("and against " + what, js[0] != scpp[i])
snull("a frequency a hertz higher", 'encode {"freq":330,"gen":"figure"}', 'encode {"freq":331,"gen":"figure"}')
snull("an old code's level one more", "decode " + code_of('{"v":1,"trig":1,"c1s":3,"level":100}'),
      "decode " + code_of('{"v":1,"trig":1,"c1s":3,"level":101}'))
snull("an old code a version later", "decode " + code_of('{"v":1,"trig":1,"c1s":3,"level":100}'),
      "decode " + code_of('{"v":2,"trig":1,"c1s":3,"level":100}'))
check("and the comparison fails against the page's lines one command out of step", sjs[1:] != scpp[:-1])
# The site's codec (5e): the compiled core's, made from the module the page
# carries and driven through the page's own wrapper, on every command above.
# Its lines are the page's to the character, throws and unreadable included.
def swasm(path):
    return subprocess.run(["node", os.path.join(HERE, "tools", "setup_js.mjs"), path], env=dict(os.environ, CORE="wasm"),
                          check=True, capture_output=True, text=True).stdout.split("\n")
swa = swasm(os.path.join(BUILD, "setup.txt"))
check("the site's codec, compiled, on all %d commands: the page's lines to the character" % len(scmds),
      swa == sjs, next(("line %d: %s | %s" % (i, a[:80], b[:80]) for i, (a, b) in enumerate(zip(swa, sjs)) if a != b), ""))
swrong = os.path.join(BUILD, "setup_wrong.txt")
with open(swrong, "w", encoding="utf-8") as f:
    f.write("\n".join(c.replace('"freq":330', '"freq":331') for c in scmds) + "\n")
check("and against the commands with a frequency a hertz higher", swasm(swrong) != sjs)

print("\n--- the clock ---")
# The page's tempo, bar, tap, MIDI clock and locked oscillators, lifted by
# name, and scope::Clock as the Brain holds it, through the same commands. A
# line a command: what reached the score and the delay, then the tempo, where
# the bar is and how it is moving, the oscillators' rates, phases and restarts.
cexe = build("clock_cpp")
def cboth(text, name="clock_one.txt"):
    path = os.path.join(BUILD, name)
    with open(path, "w") as f: f.write(text)
    js = subprocess.run(["node", os.path.join(HERE, "tools", "clock_js.mjs"), path], check=True,
                        capture_output=True, text=True).stdout
    return js, subprocess.run([cexe, path], check=True, capture_output=True, text=True).stdout
def crun(*commands): return "run\n%s\nend\n" % "\n".join(commands)
def ticks(start, gap, n, every=False):
    out = []
    for k in range(n):
        out += ["at %r" % (start + k * gap), "tick"] + (["step"] if every else [])
    return out
def cfield(line, name):
    t = line.split("|", 1)[1].split()
    return t[t.index(name) + 1]
def clfo(line, i):  # an oscillator's rate, phase and restarts
    t = line.split("|", 1)[1].split()
    k = t.index("lfo%d" % i)
    return [float(v) for v in t[k + 1:k + 4]]
cruns = [
    # A tempo changed mid-bar re-bases, so the bar does not jump.
    ("tempo-mid-bar", crun("at 0", "at 700", "tempo 90", "at 1700", "tempo 140", "at 2300", "tempo 10", "tempo 400",
                           "tempo 89.5", "tempo 90.4999")),
    # A MIDI clock at 120, its bar a twenty-fourth a tick and never past the next.
    ("midi-120", crun(*(ticks(1000, 20.833333, 30, every=True) + ["at 1700", "step", "at 1800", "step"]))),
    # Ticks bunched as USB delivers them: the tempo is the mean of the last two dozen gaps.
    ("midi-bunched", crun(*sum((["at %r" % (2000 + 83.3333 * k), "tick", "tick", "at %r" % (2000 + 83.3333 * k + 2), "tick", "tick", "step"]
                                for k in range(20)), []))),
    # The clock stops: half a second on, back to the slider from where the clock would have had the bar.
    # The clock at 125 and the slider at 100, so going back can show.
    ("midi-stops", crun("tempo 100", *(ticks(500, 20, 12, every=True) + ["at 1000", "step", "at 1300", "step", "at 1400", "step"]))),
    # A MIDI Start waits for the first tick to be the one; with no tick it lets go.
    ("start-on-clock", crun("at 300", "rt 250", "step", *ticks(320, 20.8333, 6, every=True))),
    ("start-no-clock", crun("at 300", "rt 250", "at 600", "step", "at 900", "step", "at 1200", "step")),
    # Stop holds the bar; Continue picks up at the next tick; Continue while running does nothing.
    ("stop-continue", crun("at 0", "at 1000", "stop", "at 2000", "step", "rt 251", *ticks(2010, 20.8333, 4, every=True),
                           "at 3000", "rt 251", "rt 252", "at 3500", "step", "tick", "at 4100", "step")),
    # Ticks while stopped measure the tempo and leave the bar.
    ("ticks-stopped", crun("at 100", "stop", *ticks(200, 25, 8, every=True), "start")),
    # Taps: four at 500 ms is 120, each a downbeat while running; a pause of two seconds starts again; stopped, no anchor.
    ("taps", crun("sync 0 1/4", "phase 0 1", "at 1000", "tap", "at 1500", "tap", "phase 0 2", "at 2000", "tap", "at 2500", "tap",
                  "at 3000", "tap", "at 6000", "tap", "stop", "at 6400", "tap", "at 6800", "tap")),
    ("taps-same-ms", crun("at 10", "tap", "tap", "at 20", "tap")),
    # Locked oscillators follow the tempo and the clock, and restart on Start; a free one does neither.
    ("locked", crun("sync 0 1/8t", "sync 1 4", "step", "tempo 60", "step", "phase 0 3", "phase 1 4", "start",
                    "sync 1 -", "phase 1 5", "start", "sync 1 4", *ticks(5000, 15, 10, every=True),
                    "sync 0 nonsense", "tempo 180", "step")),
    # A delay in note values is sent again when the tempo moves it, and only then.
    ("echo", crun("echo 1/8d 200", "step", "step", "tempo 100", "step", "step", "echo - 200", "tempo 120", "step",
                  "echo 1/2 300", "tempo 30", "step", "echo 1/16 300", "step", *ticks(100, 41.666, 6, every=True))),
    # More than two dozen ticks: the oldest go.
    ("many-ticks", crun(*ticks(0, 20, 40), "step")),
]
def cfuzz(n):
    out = []
    for _ in range(n):
        t, cmds = 0.0, []
        for _ in range(crng.randint(20, 90)):
            r = crng.random()
            # Now and then a step back: a MIDI tick is stamped when it arrived,
            # which can be a little before the frame that read it.
            t += crng.choice([0, 1, 5, 20.8333, 21, 40, 100, 300, 499, 501, 700, 2100]) if r < 0.9 else -crng.uniform(0, 15)
            cmds.append("at %r" % t)
            cmds.append(crng.choice(["tick", "tick", "tick", "step", "step", "tap", "start", "stop", "rt 250", "rt 251", "rt 252",
                                     "rt 248", "tempo %r" % crng.choice([60, 90, 120.5, 200, 25, 333]),
                                     "sync %d %s" % (crng.randint(0, 1), crng.choice(["-", "1/4", "1/8t", "4", "1/16", "x"])),
                                     "echo %s %d" % (crng.choice(["-", "1/8d", "1/4t", "1/16"]), crng.randint(1, 2000)),
                                     "phase %d %r" % (crng.randint(0, 1), crng.uniform(0, 6))]))
        out.append(crun(*cmds))
    return out
crng = random.Random(41)
cfuzzed = cfuzz(60)
ctext = "".join(r for _, r in cruns) + "".join(cfuzzed)
cjs, ccpp = cboth(ctext, "clock.txt")
cd = kdiff(cjs, ccpp)
check("%d runs of the clock, %d of them random, are the page's line for line" % (len(cruns) + len(cfuzzed), len(cfuzzed)),
      cd is None and len(cjs.split("\n")) > 3000, cd or "")
def cout(name):
    js, _ = cboth(dict(cruns)[name])
    return js.strip().split("\n")
L = cout("tempo-mid-bar")
check("a tempo changed mid-bar leaves the bar where it was, and the slider holds it to 30-300 in whole beats",
      cfield(L[2], "beat") == cfield(L[1], "beat") and [float(cfield(L[i], "set")) for i in (6, 7, 8, 9)] == [30, 300, 90, 90],
      "%s %s; %s" % (cfield(L[1], "beat"), cfield(L[2], "beat"), [cfield(L[i], "set") for i in (6, 7, 8, 9)]))
L = cout("midi-120")
tl = [l for l in L if l.startswith("tick")]
check("a MIDI clock at 120 reads 120, and moves the bar a twenty-fourth a tick",
      abs(float(cfield(tl[-1], "bpm")) - 120) < 1e-3 and cfield(tl[-1], "from") == "midi"
      and abs(float(cfield(tl[-1], "base")) - float(cfield(tl[-2], "base")) - 1 / 24) < 1e-12,
      "%s, %s" % (cfield(tl[-1], "bpm"), float(cfield(tl[-1], "base")) - float(cfield(tl[-2], "base"))))
check("and between ticks the bar guesses ahead but never past the next tick",
      abs(float(cfield(L[-3], "beat")) - float(cfield(L[-3], "base")) - 1 / 24) < 1e-12, cfield(L[-3], "beat"))
L = cout("midi-stops")
check("a clock gone quiet for half a second is let go, and the tempo goes back to the slider's",
      cfield(L[-5], "from") == "midi" and abs(float(cfield(L[-5], "bpm")) - 125) < 1e-9
      and cfield(L[-3], "from") == "internal" and float(cfield(L[-3], "bpm")) == 100,
      "%s %s, %s %s" % (cfield(L[-5], "from"), cfield(L[-5], "bpm"), cfield(L[-3], "from"), cfield(L[-3], "bpm")))
L = cout("start-on-clock")
first = next(l for l in L if l.startswith("tick"))
check("a MIDI Start holds the bar a tick short, so the first tick after it is the one",
      float(cfield(L[1], "base")) == -1 / 24 and float(cfield(first, "beat")) == 0 and "anchor" in L[1], first[:60])
L = cout("start-no-clock")
check("and a Start no clock follows lets go after half a second rather than holding the bar short for ever",
      float(cfield(L[-1], "beat")) > 1 and cfield(L[-1], "ticking") == "0", cfield(L[-1], "beat"))
L = cout("taps")
taps = [l for l in L if l.startswith("tap")]
check("four taps 500 ms apart are 120, each a downbeat and a restart of what is locked; after a pause of two seconds a tap starts again",
      float(cfield(taps[3], "set")) == 120 and all("anchor" in t for t in taps[1:5]) and clfo(taps[2], 0)[1:] == [0, 2]
      and "anchor" not in taps[5] and cfield(taps[5], "taps") == "1",
      " / ".join(cfield(t, "set") for t in taps))
check("and stopped, a tap sets the tempo and restarts the oscillators, but leaves the bar where it stood",
      float(cfield(taps[6], "set")) == 150 and "anchor" not in taps[6] and clfo(taps[6], 0)[2] == 5
      and cfield(taps[6], "beat") == cfield(taps[5], "beat"), taps[6][:80])
L = cout("locked")
last_tick_step = [l for l in L if l.startswith("step") and cfield(l, "from") == "midi"][-1]
check("a locked oscillator runs at the tempo's note value, follows a MIDI clock, and restarts on Start; a free one does neither",
      abs(clfo(L[2], 0)[0] - 6) < 1e-12 and abs(clfo(L[4], 0)[0] - 3) < 1e-12 and abs(clfo(L[4], 1)[0] - 1 / 16) < 1e-12
      and clfo(L[7], 0)[1:] == [0, 1] and clfo(L[10], 1)[1:] == [5, 1]
      and abs(clfo(last_tick_step, 1)[0] - float(cfield(last_tick_step, "bpm")) / 960) < 1e-12
      and float(cfield(last_tick_step, "bpm")) != 60 and clfo(L[-1], 0)[0] == clfo(L[-4], 0)[0],
      "%s %s %s | %s | %s | %s" % (clfo(L[2], 0), clfo(L[4], 0), clfo(L[4], 1), clfo(L[7], 0), clfo(L[10], 1), clfo(last_tick_step, 1)))
L = cout("echo")
sent = [i for i, l in enumerate(L) if ":: delayMs" in l]
said = [L[i].split(":: ")[1].split(" |")[0] for i in sent]
check("a delay in note values is sent when the tempo moves it, not again until it does, and never past two seconds",
      sent[:4] == [1, 4, 11, 13] and said[:4] == ["delayMs 375", "delayMs 450", "delayMs 2000", "delayMs 500"],
      "%s %s" % (sent[:5], said[:5]))
# Nulls: the page told something different, and the port must disagree.
def cnull(what, name, old, new):
    text = dict(cruns)[name]
    assert text.count(old) >= 1
    js, _ = cboth(text.replace(old, new, 1))
    _, cpp = cboth(text)
    check("and against " + what, kdiff(js, cpp) is not None)
cnull("a tempo a beat a minute faster", "tempo-mid-bar", "tempo 90\n", "tempo 91\n")
cnull("a tick a millisecond late", "midi-120", "at 1041.666666", "at 1042.666666")
cnull("an oscillator locked to a quaver instead of a quaver triplet", "locked", "sync 0 1/8t", "sync 0 1/8")
cnull("a Continue instead of a Start", "start-on-clock", "rt 250", "rt 251")
check("and the comparison fails against the page's lines one command out of step",
      kdiff("\n".join(cjs.split("\n")[1:]), "\n".join(ccpp.split("\n")[:-1])) is not None)

print("\n--- the level and the threshold ---")
# The page's `env.live` - an envelope follower over the screen's signal lane -
# and K1's threshold, a value made into an event, lifted by name, against
# scope::Level and the Brain's threshold, through the same commands. A line a
# command: the follower and the source's value, then the threshold's count,
# whether it is armed, when it last fired, its flash, and whether it is a loop.
lvexe = build("signal_cpp")
def lvboth(text, name="signal_one.txt"):
    path = os.path.join(BUILD, name)
    with open(path, "w") as f: f.write(text)
    js = subprocess.run(["node", os.path.join(HERE, "tools", "signal_js.mjs"), path], check=True,
                        capture_output=True, text=True).stdout
    return js, subprocess.run([lvexe, path], check=True, capture_output=True, text=True).stdout
def lvrun(*commands): return "run\n%s\nend\n" % "\n".join(commands)
lvruns = [
    # A tone half full scale for a third of a second, then silence for a second: fast up, slow down.
    ("level-rise", lvrun("sine 0.5 8 2048", *["frame 16"] * 20, "sine 0 1 2048", *["frame 16"] * 60)),
    # The stride, a 512th of the lane rounded down: 511 and 1023 read every sample, 1024 and 1533 every other, 1536
    # and 2047 every third, 4096 every eighth. 1533 and 2047 are where a 511th would give one more.
    ("level-stride", lvrun(*sum((["noise %d 0.8 %d" % (n, n), "frame 33"] for n in (511, 512, 1023, 1024, 1025, 1533, 1536, 2047, 4096)), []))),
    # A full-scale sine is one; louder is still one, while the follower goes on rising.
    ("level-full", lvrun("sine 1 4 1024", *["frame 50"] * 10, "sine 1.6 4 1024", *["frame 50"] * 10)),
    # Rising through the level fires once; falling short of the hysteresis does not arm it; 80 ms must pass.
    ("thresh-fire", lvrun("watch test.v", "level 0.5", "at 0", "v 0.2", "thresh", "at 10", "v 0.6", "thresh", "at 20", "thresh",
                         "at 30", "v 0.47", "thresh", "at 40", "v 0.44", "thresh", "at 50", "v 0.6", "thresh", "at 89", "thresh",
                         "at 90", "thresh", "at 200", "v 0.1", "thresh", "at 300", "v 0.5", "thresh", "at 400", "thresh")),
    # The gap and the level, each exactly: 80 ms after the last is allowed, the level itself is through it. And
    # the hysteresis: 0.3 - 0.05 is 0.24999999999999997 in doubles, so 0.25 is not below it and 0.2499 is.
    ("thresh-exact", lvrun("watch test.v", "level 0.3", "at 1000", "v 0", "thresh", "v 0.3", "thresh", "v 0.2", "thresh",
                          "at 1079", "v 0.3", "thresh", "at 1080", "thresh", "v 0.25", "thresh", "at 1500", "v 0.3", "thresh",
                          "v 0.2499", "thresh", "at 2000", "v 0.3", "thresh")),
    # What it watches: an event source disarms it, the picture's makes it a loop, nothing is nothing, itself is an event.
    ("thresh-kinds", lvrun("watch test.v", "v 0", "thresh", "watch test.e", "thresh", "v 0.9", "thresh", "watch test.p", "v 0",
                          "thresh", "v 0.9", "at 100", "thresh", "watch nothing", "thresh", "watch threshold", "thresh",
                          "watch test.v", "v 0", "thresh", "v 0.9", "at 300", "thresh")),
    # The source it watches forgotten, as a controller can be, and moved again: it has to fall below again first.
    ("thresh-forgot", lvrun("watch test.v", "level 0.5", "at 0", "v 0", "thresh", "drop", "at 100", "thresh", "add", "v 0.9",
                           "at 200", "thresh", "v 0", "at 300", "thresh", "v 0.9", "at 400", "thresh")),
    # A setup loaded: what it watches and its level from the code, and armed afresh. 120 is held to 95 hundredths, so
    # 0.96 is through it; 1 to 5, so nought cannot arm it (0.05 - 0.05 is not below nought) and a hair under can.
    ("thresh-restore", lvrun("watch test.v", "at 0", "v 0", "thresh", "restore test.v 60", "v 0.9", "at 100", "thresh",
                            "v 0", "at 200", "thresh", "restore test.p 120", "v 0.96", "at 300", "thresh", "v 0", "at 400", "thresh",
                            "v 0.96", "at 500", "thresh", "restore test.v 1", "v 0", "at 600", "thresh", "v -0.01", "at 650", "thresh",
                            "v 0.06", "at 700", "thresh")),
    # Watching the level itself, the default: a tone arriving fires it.
    ("thresh-level", lvrun("level 0.3", "sine 0 1 1024", "at 0", "frame 16", "thresh", *sum((["at %d" % (16 * k), "sine 0.6 3 1024" if k == 4 else "frame 16",
                          "frame 16", "thresh"] for k in range(1, 30)), []))),
]
def lvfuzz(n):
    out = []
    for _ in range(n):
        t, cmds = 0, ["watch " + lvrng.choice(["test.v", "env.live", "test.p", "test.e"])]
        for _ in range(lvrng.randint(30, 120)):
            t += lvrng.choice([0, 1, 16, 33, 79, 80, 81, 200])
            cmds.append("at %d" % t)
            r = lvrng.random()
            if r < 0.3: cmds.append("thresh")
            elif r < 0.5: cmds.append("v %r" % lvrng.choice([0, 0.1, 0.44, 0.45, 0.46, 0.5, 0.55, 0.9, 1.2, -0.3]))
            elif r < 0.65: cmds.append("frame %r" % lvrng.choice([0, 1, 16, 16.7, 33, 100, 1000]))
            elif r < 0.72: cmds.append("sine %r %d %d" % (lvrng.choice([0, 0.1, 0.5, 1, 1.5]), lvrng.randint(1, 12), lvrng.choice([100, 511, 512, 1024, 1025, 2048])))
            elif r < 0.78: cmds.append("noise %d %r %d" % (lvrng.randint(1, 99), lvrng.choice([0.2, 0.7, 1]), lvrng.choice([300, 512, 777, 2049])))
            elif r < 0.86: cmds.append("level %r" % lvrng.choice([0.05, 0.3, 0.5, 0.95]))
            elif r < 0.93: cmds.append("watch " + lvrng.choice(["test.v", "test.v", "env.live", "test.p", "test.e", "threshold", "nothing"]))
            elif r < 0.96: cmds.append(lvrng.choice(["drop", "add"]))
            else: cmds.append("restore %s %r" % (lvrng.choice(["test.v", "env.live", "test.p", "nothing"]), lvrng.choice([1, 30, 50, 95, 200])))
        out.append(lvrun(*cmds))
    return out
lvrng = random.Random(47)
lvfuzzed = lvfuzz(60)
lvtext = "".join(r for _, r in lvruns) + "".join(lvfuzzed)
lvjs, lvcpp = lvboth(lvtext, "signal.txt")
lvd = kdiff(lvjs, lvcpp)
check("%d runs of the level and the threshold, %d of them random, are the page's line for line" % (len(lvruns) + len(lvfuzzed), len(lvfuzzed)),
      lvd is None and len(lvjs.split("\n")) > 4000, lvd or "%d lines" % len(lvjs.split("\n")))
def lvout(name):
    js, _ = lvboth(dict(lvruns)[name])
    return js.strip().split("\n")
def lvfield(line, name):
    t = line.split(" | ")[-1].split()
    return t[t.index(name) + 1]
L = lvout("level-rise")
env = [float(lvfield(l, "env")) for l in L if l.startswith("frame")]
# 0.5 / sqrt(2) is the tone's RMS. Attack: 16 ms steps on a 20 ms time constant, so the first step is 1 - e^-0.8 of the way.
rms = 0.5 / math.sqrt(2)
up = next(i for i, e in enumerate(env) if e > rms / 2)
down = next(i for i, e in enumerate(env[20:]) if e < env[19] / 2)
check("the level rises to a tone's RMS on a 20 ms attack and falls on a 250 ms release, twelve and a half times as slow",
      abs(env[0] - rms * (1 - math.exp(-0.8))) < 1e-6 and abs(env[19] - rms) < 1e-4 and up == 0 and 9 <= down <= 12,
      "first step %.5f, after 20 frames %.5f of %.5f, half way down after %d frames" % (env[0], env[19], rms, down))
L = lvout("level-full")
check("a full-scale sine reads one, and louder reads one still, while the follower itself goes on up",
      abs(float(lvfield(L[10], "level")) - 1) < 2e-3 and lvfield(L[-1], "level") == "1.0000000000000000" and float(lvfield(L[-1], "env")) > 1.1,
      "%s, then %s at %s" % (lvfield(L[10], "level"), lvfield(L[-1], "level"), lvfield(L[-1], "env")))
L = lvout("thresh-fire")
counts = [int(lvfield(l, "count")) for l in L if l.startswith("thresh")]
# thresh at 0 (arms), 10 fires, 20 no, 30 (0.47, not re-armed), 40 (0.44, arms), 50 (0.6, 40 ms after the last: no), 89 no, 90 fires,
# 200 arms, 300 (0.5, the level itself) fires, 400 no.
check("rising through the level fires once; falling short of the hysteresis does not arm it again; 80 ms must pass; the level itself is through",
      counts == [0, 1, 1, 1, 1, 1, 1, 2, 2, 3, 3], str(counts))
L = lvout("thresh-exact")
counts = [int(lvfield(l, "count")) for l in L if l.startswith("thresh")]
check("80 ms after the last firing is allowed and 79 is not; 0.05 below the level does not arm it, a hair more below does",
      counts == [0, 1, 1, 1, 2, 2, 2, 2, 3], str(counts))
L = lvout("thresh-kinds")
th = [l for l in L if l.startswith("thresh")]
check("watching an event source disarms it and never fires; watching the picture's makes it a loop; nothing and itself are nothing",
      [int(lvfield(l, "count")) for l in th] == [0, 0, 0, 0, 1, 1, 1, 1, 2] and lvfield(th[3], "loop") == "1"
      and all(lvfield(l, "loop") == "0" for l in th[:3] + th[5:]) and lvfield(th[1], "armed") == "0",
      str([(lvfield(l, "count"), lvfield(l, "armed"), lvfield(l, "loop")) for l in th]))
L = lvout("thresh-forgot")
counts = [int(lvfield(l, "count")) for l in L if l.startswith("thresh")]
check("the source it watches forgotten and brought back has to fall below the level again before it fires",
      counts == [0, 0, 0, 0, 1], str(counts))
L = lvout("thresh-restore")
th = [l for l in L if l.startswith("thresh")]
check("a setup loaded sets what it watches and its level, held within 5 and 95 hundredths, and arms it afresh",
      [int(lvfield(l, "count")) for l in th] == [0, 0, 0, 0, 0, 1, 1, 1, 2] and lvfield(th[0], "armed") == "1"
      and lvfield(th[1], "armed") == "0" and lvfield(th[3], "loop") == "1" and lvfield(th[6], "armed") == "0",
      str([(lvfield(l, "count"), lvfield(l, "armed"), lvfield(l, "loop")) for l in th]))
L = lvout("thresh-level")
fired = next((l for l in L if l.startswith("thresh") and lvfield(l, "count") == "1"), None)
check("watching the level, as it does unless told otherwise, a tone arriving fires it once",
      fired is not None and lvfield(L[-1], "count") == "1" and 0.3 <= float(lvfield(fired, "level")) < 0.6,
      fired[:100] if fired else "never fired")
def lvnull(what, name, old, new):
    text = dict(lvruns)[name]
    assert text.count(old) >= 1, old
    js, _ = lvboth(text.replace(old, new, 1))
    _, cpp = lvboth(text)
    check("and against " + what, kdiff(js, cpp) is not None)
lvnull("the tone a twentieth louder", "level-rise", "sine 0.5 8 2048", "sine 0.525 8 2048")
lvnull("a lane one sample longer", "level-stride", "noise 1024 0.8 1024", "noise 1024 0.8 1025")
lvnull("the level a hundredth higher, over the value it is crossed by", "thresh-exact", "level 0.3", "level 0.31")
lvnull("a firing a millisecond later", "thresh-fire", "at 90", "at 91")
check("and the comparison fails against the page's lines one command out of step",
      kdiff("\n".join(lvjs.split("\n")[1:]), "\n".join(lvcpp.split("\n")[:-1])) is not None)

print("\n--- the capture ---")
# The page's capture - the window and the search span behind it, the AC
# coupling, the filter, the lag lane, mid and side, the turn and the trigger -
# lifted by name, against scope/capture.h, through the same commands. A line
# a frame: whether it triggered, the level as a voltage, what it asked the
# source for, the window and where the edge sits in it, whether it turned,
# what the coupling and the filter changed, the lag used, how short the
# buffer was, and every lane drawn and measured, by two sums and its ends.
cpexe = build("capture_cpp")
def cpboth(text, name="capture_one.txt"):
    path = os.path.join(BUILD, name)
    with open(path, "w") as f: f.write(text)
    js = subprocess.run(["node", os.path.join(HERE, "tools", "capture_js.mjs"), path], check=True,
                        capture_output=True, text=True).stdout
    return js, subprocess.run([cpexe, path], check=True, capture_output=True, text=True).stdout
def cprun(*commands): return "run\n%s\nend\n" % "\n".join(commands)
TONE = ["signal 40000", "add 0 sine 0.5 220 0", "add 1 sine 0.3 330 1"]
cpruns = [
    # Every timebase at three rates, with the edge a tenth in, half way and at the very end.
    ("window", cprun(*TONE, *[x for r in (48000, 44100, 96000) for x in ["rate %d" % r] + [y for t in range(9) for y in ("tb %d" % t, "cap")]],
                     "rate 48000", "tb 3", "pos 0", "cap", "pos 0.5", "cap", "pos 1", "cap", "posmod 0.3", "cap", "posmod -2", "cap")),
    # The edge: rising and falling, at levels inside and outside the signal,
    # on noise where the hysteresis matters, with holdoff on a ringing square,
    # and none at all on a constant - the window runs free.
    ("trigger", cprun("signal 30000", "add 0 sine 0.5 220 0", "add 0 noise 3 0.05", "add 1 square 0.4 110 0", "add 1 sine 0.1 2200 0",
                      "tb 3", "cap", "level 0.3", "cap", "edge falling", "cap", "level 0.7", "cap", "level -0.45", "cap",
                      "edge rising", "trig 1", "level 0", "cap", "holdoff 3", "cap", "holdoff 8", "cap", "holdoff 50", "cap",
                      "signal 30000", "add 0 dc 0.2", "trig 0", "holdoff 0", "cap")),
    # Full scale: the level a fraction of the screen, so a voltage that
    # follows the lane's scale and what is pointed at it.
    ("fullscale", cprun(*TONE, "tb 3", "level 0.4", "cap", "fs 0 -6", "cap", "fs 0 -12", "fsmod 0 -6", "cap", "fsmod 0 -90", "cap",
                        "fs 0 3", "fsmod 0 0", "cap")),
    # The coupling: an offset taken off one lane and not the other, the
    # corner held to its range, and nothing taken off on the input's side.
    ("ac", cprun("signal 40000", "add 0 sine 0.3 220 0", "add 0 dc 0.4", "add 1 sine 0.3 220 0", "add 1 dc 0.4", "tb 4",
                 "ac 0 1", "cap", "achz 0.1", "cap", "achz 100", "cap", "ac 1 1", "trig 1", "cap", "shaping 0", "cap")),
    # The filter, each kind, its resonance and what is pointed at both; a
    # lane switched off left alone; the input's side left alone.
    ("filter", cprun("signal 40000", "add 0 square 0.4 220 0", "add 1 noise 5 0.3", "tb 3",
                     *[y for t in ("lowpass", "highpass", "bandpass", "notch") for y in ("filter %s 500 0" % t, "cap", "filter %s 700 80" % t, "cap")],
                     "fmod 200 10", "cap", "fmod -2000 500", "cap", "fmod 0 0", "on 1 0", "cap", "on 1 1", "shaping 0", "cap",
                     "shaping 1", "filter off", "cap")),
    # The lag lane: a whole and a fractional delay, its modulation, the most
    # it may be, an automatic lock, and the three things that refuse it - mid
    # and side, a source of lanes, and a buffer with no room for it.
    ("lag", cprun(*TONE, "tb 3", "lag 2", "cap", "lag 1.37", "cap", "lagmod 0.5", "cap", "lag 90", "cap", "lagmod 0",
                  "lagauto 0.00113", "cap", "lagauto none", "lag 1", "ms 1", "cap", "ms 0", "lanes 1", "cap", "lanes 0",
                  "cap 1000", "cap", "cap inf", "lagoff", "cap")),
    # Mid and side, with two lanes and with one; and the turn, a quarter and
    # by modulation, refused for a source of lanes, a lag, and the input's side.
    ("turn", cprun(*TONE, "tb 3", "ms 1", "cap", "chans 1", "cap", "chans 2", "ms 0", "rot 0.25", "cap", "rotmod 0.1", "cap",
                   "measure 1", "cap", "measure 0", "lanes 1", "cap", "lanes 0", "lag 1", "cap", "lagoff", "shaping 0", "cap",
                   "shaping 1", "level 0.2", "cap")),
    # The buffer: the search span giving way first, then the window short
    # and said so; six lanes and one, the trigger on a lane switched off.
    ("buffer", cprun(*TONE, "tb 4", "cap 3000", "cap", "cap 900", "cap", "cap 500", "tb 6", "cap", "cap inf", "chans 6",
                     "add 4 sine 0.2 440 0", "trig 4", "cap", "on 4 0", "cap", "trig 9", "cap", "chans 1", "trig 0", "cap")),
]
cpruns += [
    # Samples landing exactly on the level and on the hysteresis band's
    # edge: a square of a half on an offset of a half is exactly nought and
    # exactly one, so a level of one is met and not passed, and a level of
    # 0.02 puts the band's edge at nought itself. Its edges are exactly 480
    # samples apart - a phase off nought, so no edge sits where the sine is
    # nought and its sign is rounding - and so a holdoff of exactly that, and
    # one that rounds to it from above. Last, the band's edge at nought with
    # the window starting at the edge, so the first edge of all is in reach
    # and only arming refuses it.
    ("exact", cprun("signal 30000", "add 0 square 0.5 100 0.1", "add 0 dc 0.5", "tb 3", "pos 0.5",
                    "level 1", "cap", "level 0.02", "cap", "level 0.5", "holdoff 10", "cap",
                    "holdoff 10.0083333333", "cap", "holdoff 9.99", "cap", "holdoff 0", "pos 0", "level 0.02", "cap")),
    # The probe: the trigger on a lane switched off measures lane one's coupling instead.
    ("probe", cprun("signal 40000", "add 0 sine 0.3 220 0", "add 0 dc 0.4", "add 1 sine 0.3 330 0", "add 1 dc 0.1", "tb 4",
                    "ac 0 1", "ac 1 1", "trig 1", "cap", "on 1 0", "cap", "filter lowpass 300 0", "cap")),
    # A cutoff past what the rate can hold, and a lag that adds to less than nothing.
    ("edges", cprun(*TONE, "rate 22050", "tb 3", "filter lowpass 1000 0", "cap", "filter highpass 990 50", "cap", "rate 48000",
                    "filter off", "cap 3000", "lag 1", "lagmod -5", "cap")),
]
cprng = random.Random(105)
def cpfuzz(n):
    out = ["rate %d" % cprng.choice([44100, 48000, 96000]), "signal %d" % cprng.choice([20000, 40000, 60000])]
    for c in range(cprng.randint(1, 4)):
        for _ in range(cprng.randint(1, 3)):
            k = cprng.choice(["sine", "square", "noise", "dc"])
            out.append("add %d %s" % (c, {"sine": "sine %.2f %.1f %.2f" % (cprng.random(), cprng.uniform(20, 3000), cprng.uniform(0, 6)),
                                          "square": "square %.2f %.1f %.2f" % (cprng.random(), cprng.uniform(20, 1000), cprng.uniform(0, 6)),
                                          "noise": "noise %d %.2f" % (cprng.randint(1, 99), cprng.random() * 0.4),
                                          "dc": "dc %.2f" % cprng.uniform(-0.5, 0.5)}[k]))
    out.append("chans %d" % cprng.choice([1, 2, 2, 2, 4]))
    for _ in range(n):
        r = cprng.random()
        pick = cprng.choice
        if r < 0.3: out.append("cap")
        elif r < 0.36: out.append("tb %d" % cprng.randint(0, 8))
        elif r < 0.42: out.append(pick(["pos %.2f" % cprng.random(), "posmod %.2f" % cprng.uniform(-0.5, 0.5), "holdoff %d" % pick([0, 0, 2, 10])]))
        elif r < 0.5: out.append(pick(["level %.2f" % cprng.uniform(-1, 1), "edge %s" % pick(["rising", "falling"]), "trig %d" % cprng.randint(0, 4)]))
        elif r < 0.56: out.append(pick(["ac %d %d" % (cprng.randint(0, 3), cprng.random() < 0.5), "achz %.1f" % cprng.uniform(0, 30)]))
        elif r < 0.62: out.append(pick(["fs %d %d" % (cprng.randint(0, 3), pick([0, -3, -12, -50, 6])), "fsmod %d %.1f" % (cprng.randint(0, 3), cprng.uniform(-20, 5)),
                                        "on %d %d" % (cprng.randint(0, 3), cprng.random() < 0.7)]))
        elif r < 0.7: out.append(pick(["filter %s %d %d" % (pick(["lowpass", "highpass", "bandpass", "notch"]), cprng.randint(0, 1000), cprng.randint(0, 100)),
                                       "filter off", "fmod %d %d" % (cprng.randint(-300, 300), cprng.randint(-50, 50))]))
        elif r < 0.78: out.append(pick(["lag %.2f" % cprng.uniform(0, 50), "lagoff", "lagmod %.2f" % cprng.uniform(-2, 2),
                                        "lagauto %s" % pick(["none", "%.5f" % cprng.uniform(0, 0.03)])]))
        elif r < 0.86: out.append(pick(["ms %d" % (cprng.random() < 0.3), "rot %.3f" % pick([0, 0, cprng.uniform(-1, 1)]), "rotmod %.3f" % cprng.uniform(-0.2, 0.2)]))
        elif r < 0.92: out.append(pick(["shaping %d" % (cprng.random() < 0.8), "measure %d" % (cprng.random() < 0.5), "lanes %d" % (cprng.random() < 0.2)]))
        else: out.append("cap %s" % pick(["inf", "inf", str(cprng.randint(500, 40000))]))
    return cprun(*out)
cpruns += [("random-%d" % i, cpfuzz(60)) for i in range(40)]
cptext = "".join(t for _, t in cpruns)
cpjs, cpcpp = cpboth(cptext, "capture.txt")
cplines = [len(t.strip().split("\n")) - 2 for _, t in cpruns]
def cpslice(out, i):
    lines = out.strip().split("\n")
    start = sum(cplines[:i])
    return "\n".join(lines[start:start + cplines[i]])
for i, (name, _) in enumerate(cpruns):
    if name.startswith("random-"): continue
    d = kdiff(cpslice(cpjs, i), cpslice(cpcpp, i))
    check("%s: %d commands, the same frames" % (name, cplines[i]), d is None, d or "")
cpbad = [n for i, (n, _) in enumerate(cpruns) if n.startswith("random-") and kdiff(cpslice(cpjs, i), cpslice(cpcpp, i))]
check("40 random sequences of 60 commands, the same frames", not cpbad, ", ".join(cpbad))
def cpframes(name): return [l for l in cpslice(cpjs, next(i for i, (n, _) in enumerate(cpruns) if n == name)).split("\n") if l.startswith("cap ")]
def cpf(line, word, k=0): w = line.split(); return w[w.index(word) + 1 + k]
wn = cpframes("window")
check("2 ms a division is 960 samples at 48 kHz, 882 at 44.1 and 1920 at 96; the edge a tenth in, then half way, then at the end",
      cpf(wn[4], "len") == "960" and cpf(wn[13], "len") == "882" and cpf(wn[22], "len") == "1920" and cpf(wn[27], "pre") == "0"
      and cpf(wn[28], "pre") == "240" and cpf(wn[29], "pre") == "480" and cpf(wn[0], "len") == "64",
      " ".join(cpf(wn[k], "len") for k in (0, 4, 13, 22)))
tr = cpframes("trigger")
check("the trigger finds edges on noise and on a ringing square, and runs free at a level the signal never reaches and on a constant",
      all(cpf(l, "trig") == "1" for l in tr[:3] + tr[4:9]) and cpf(tr[3], "trig") == "0" and cpf(tr[-1], "trig") == "0",
      " ".join(cpf(l, "trig") for l in tr))
fsl = cpframes("fullscale")
check("the level follows full scale: 0.4 of the screen is 0.2 volts at -6 dB, and full scale is held to its range",
      abs(float(cpf(fsl[1], "level")) - 0.4 * 10 ** (-6 / 20)) < 1e-12 and float(cpf(fsl[3], "level")) == float(cpf(fsl[3], "level"))
      and abs(float(cpf(fsl[3], "level")) - 0.4 * 10 ** (-50 / 20)) < 1e-12 and abs(float(cpf(fsl[4], "level")) - 0.4) < 1e-12,
      " ".join(cpf(l, "level") for l in fsl))
acl = cpframes("ac")
check("the coupling takes an offset off the lane it is on, and nothing on the input's side",
      float(cpf(acl[0], "shaped")) > 0.1 and float(cpf(acl[4], "shaped")) == 0, " ".join(cpf(l, "shaped") for l in acl))
lg = cpframes("lag")
check("the lag lane is two milliseconds, held to forty, and refused with mid and side, with lanes and with no room",
      abs(float(cpf(lg[0], "lag")) - 2) < 1e-9 and abs(float(cpf(lg[3], "lag")) - 40) < 1e-9 and float(cpf(lg[5], "lag")) == 0
      and float(cpf(lg[6], "lag")) == 0 and float(cpf(lg[7], "lag")) == 0, " ".join(cpf(l, "lag") for l in lg))
tn = cpframes("turn")
check("the turn turns the screen's pair and not what is measured, and is refused for lanes, a lag and the input's side",
      cpf(tn[2], "turned") == "1" and cpf(tn[2], "measured") == "signal" and cpf(tn[4], "measured") == "drawn"
      and cpf(tn[5], "turned") == "0" and cpf(tn[6], "turned") == "0" and cpf(tn[7], "turned") == "0")
bf = cpframes("buffer")
check("a short buffer gives up the search span first, then draws a window it says is short",
      int(cpf(bf[0], "asked")) <= 3000 and cpf(bf[0], "starved") == "0" and int(cpf(bf[2], "starved")) > 0, " ".join(cpf(l, "asked") + "/" + cpf(l, "starved") for l in bf))
def cpnull(name, old, new, what):
    text = dict(cpruns)[name]
    assert old in text, old
    js, _ = cpboth(text.replace(old, new, 1))
    i = next(k for k, (n, _) in enumerate(cpruns) if n == name)
    check("and against " + what, kdiff(js, cpslice(cpcpp, i)) is not None)
cpnull("trigger", "level 0.3", "level 0.31", "a level a hundredth higher")
cpnull("filter", "filter lowpass 500 0", "filter lowpass 501 0", "a cutoff a step higher")
cpnull("lag", "lag 1.37", "lag 1.38", "a lag a hundredth of a millisecond longer")
cpnull("turn", "rot 0.25", "rot 0.251", "a turn a thousandth further")
check("and the comparison fails against the page's lines one command out of step",
      kdiff("\n".join(cpjs.strip().split("\n")[1:]), "\n".join(cpcpp.strip().split("\n")[:-1])) is not None)

print("\n--- the beam's walk ---")
# What the page's renderer lays into the phosphor grid - drawMain's Y-T lanes,
# as peak bars and as the polyline, and drawXY's figure or figures, with the
# beam's shading on either - against scope/beam.h, each frame taken by the
# capture of the side it belongs to. A line a frame: the grid by two sums, the
# beam's path by its roundness, the fades counted, the graticule, and every
# anchor the beam holds.
bmexe = build("beam_cpp")
def bmboth(text, name="beam_one.txt"):
    path = os.path.join(BUILD, name)
    with open(path, "w") as f: f.write(text)
    # With a time limit: the walk once took a hundred million steps over one
    # loud sample, and a hang should fail the check rather than the suite.
    js = subprocess.run(["node", os.path.join(HERE, "tools", "beam_js.mjs"), path], check=True,
                        capture_output=True, text=True, timeout=300).stdout
    return js, subprocess.run([bmexe, path], check=True, capture_output=True, text=True, timeout=300).stdout
bmruns = [
    # The figure: each level of the beam, one the page has no ramp for, the
    # beam off, X-Y's own switch, the zoom, an offset and a full scale, the
    # smallest square the page will draw, and a resize.
    ("xy", cprun(*TONE, "display xy", "tb 3", "persist 0.2", "draw 16", "draw 16", "beam subtle", "draw 16", "beam high", "draw 33",
                 "beam bright", "draw 16", "beam off", "draw 16", "beam moderate", "beamxy 0", "draw 16", "beamxy 1", "zoom 3", "draw 16",
                 "offset 0 0.3", "fs 1 -6", "draw 16", "canvas 60 50", "resize", "draw 16", "canvas 800 500", "resize", "draw 0", "draw 2000")),
    # A diagonal line - both lanes one signal, so a turn is plain to see -
    # unturned, turned by the capture as a stereo pair, turned by the walk as a
    # rack, by modulation, not at all on the input's side, and with the lag.
    # Unshaded, because this is about where the line goes: the capture rounds
    # the lanes it turns to floats and the walk turns in doubles, and the beam
    # reads lengths through a histogram whose bins that rounding can cross -
    # which shaded a pair turned one way a whole step apart from the same pair
    # turned the other, or against the speed of the picture before.
    ("turn", cprun("signal 40000", "add 0 sine 0.6 220 0", "add 1 sine 0.6 220 0", "display xy", "beamxy 0", "tb 3", "draw 16", "rot 0.125",
                   "draw 16", "lanes 1", "draw 16", "rotmod 0.05", "draw 16", "shaping 0", "draw 16", "shaping 1", "lanes 0", "rotmod 0",
                   "lag 1", "beamxy 1", "draw 16")),
    # Figures the source asks for: two, one naming a lane that is not there,
    # one alone, none and the pair the menus chose, and the lag refusing them.
    ("figures", cprun(*TONE, "add 2 sine 0.4 110 0", "add 3 sine 0.4 165 0.5", "chans 4", "display xy", "tb 3", "figures 0,1;2,3", "draw 16",
                      "figures 0,1;2,5", "draw 16", "figures none", "draw 16", "figures 2,3", "draw 16", "figures none", "pair 1 0", "draw 16",
                      "pair 0 3", "draw 16",
                      "pair 0 1", "figures 0,1;2,3", "beamxy 0", "draw 16", "beamxy 1", "lag 1", "draw 16")),
    # A long window: eight samples a point, four, and every sample.
    ("stride", cprun("rate 96000", "signal 500000", "add 0 sine 0.5 50 0", "add 1 sine 0.5 75 0.3", "display xy", "tb 8", "draw 16",
                     "tb 7", "draw 16", "tb 5", "draw 16")),
    # Y-T: the polyline, then shaded, magnified, peak bars, the polyline again
    # under a deep zoom, a wide screen shaded both sides of the beam's limit
    # and past it, and a constant the trigger cannot lock to, which the beam
    # leaves unshaded.
    ("yt", cprun(*TONE, "tb 3", "draw 16", "beamyt 1", "draw 16", "draw 16", "zoom 4", "draw 16", "tb 6", "zoom 1", "draw 16", "zoom 16",
                 "draw 16", "zoom 1", "canvas 4000 500", "resize", "tb 5", "draw 16", "tb 6", "draw 16", "tb 7", "draw 16",
                 "rate 96000", "canvas 5000 500", "tb 6", "draw 16", "rate 48000", "canvas 800 500", "signal 40000", "add 0 dc 0.2",
                 "add 1 dc -0.1", "tb 3", "draw 16")),
    # Six lanes stacked, with the gutter set by the widest name and held to 22
    # per cent of the screen, rounded to a whole pixel; overlaid; a lane off, one offset, one scaled; and
    # two lanes, which are never stacked.
    ("stack", cprun("signal 40000", *["add %d sine %.1f %d %d" % (c, 0.3 + 0.1 * c, 110 * (c + 1), c) for c in range(6)], "chans 6", "tb 3",
                    "draw 16", "name 40.2", "draw 16", "name 300", "draw 16", "stack 0", "draw 16", "canvas 801 500", "stack 1", "draw 16",
                    "canvas 800 500", "on 2 0", "offset 3 0.5",
                    "fs 4 -12", "beamyt 1", "draw 16", "chans 2", "draw 16")),
    # Persistence: infinite, a half, a resize and off.
    ("persist", cprun(*TONE, "display xy", "tb 3", "persist -1", "draw 16", "draw 16", "draw 16", "persist 0.5", "draw 16", "resize",
                      "draw 16", "persist 0", "draw 16")),
    # The anchor: set, moved part way by a figure ten times faster, further
    # over a longer frame, forgotten and set afresh, and the floor on the time.
    ("anchor", cprun(*TONE, "display xy", "tb 3", "draw 16", "signal 40000", "add 0 sine 0.5 2200 0", "add 1 sine 0.3 3300 1", "draw 16",
                     "draw 500", "forget", "draw 16", "draw 0")),
    # A lane that is not a number, and one that goes from loud to infinite in
    # a window, through every walk: nothing laid where there is no number,
    # and the long segments cut to the grid.
    ("loud", cprun(*TONE, "add 1 dc NaN", "tb 3", "draw 16", "display xy", "draw 16", "signal 40000", "add 0 sine 0.5 220 0",
                   "add 1 sine 1e39 330 0", "display yt", "draw 16", "display xy", "draw 16", "beamyt 1", "display yt", "draw 16", "tb 7", "draw 16")),
    # A figure that does not move, so every length is the floor; the deepest
    # zoom, where nearly every segment is cut; Y-T's sixteen-sample least; and
    # noise ten times full scale at that zoom, every segment long enough to be
    # past the anchor's histogram.
    ("edges", cprun("signal 40000", "add 0 dc 0.3", "add 1 dc 0.3", "display xy", "tb 3", "draw 16", *TONE, "zoom 64", "draw 16",
                    "display yt", "draw 16", "beamyt 1", "draw 16", "signal 40000", "add 0 noise 3 0.9", "add 1 noise 4 0.9",
                    "fs 0 -20", "fs 1 -20", "display xy", "forget", "draw 16")),
    # A circle and a fifth, beam on then off.
    ("circle", cprun("signal 40000", "add 0 sine 0.5 220 0", "add 1 sine 0.5 220 1.5707963267948966", "display xy", "tb 3", "draw 16",
                     "beamxy 0", "draw 16", "beamxy 1", *TONE, "draw 16", "beamxy 0", "draw 16")),
]
bmrng = random.Random(110)
def bmfuzz(n):
    chans = bmrng.choice([1, 2, 2, 4])
    out = ["rate %d" % bmrng.choice([44100, 48000, 96000]), "signal %d" % bmrng.choice([40000, 60000]), "chans %d" % chans]
    for c in range(chans):
        for _ in range(bmrng.randint(1, 2)):
            k = bmrng.choice(["sine", "sine", "square", "noise", "dc"])
            out.append("add %d %s" % (c, {"sine": "sine %.2f %.1f %.2f" % (bmrng.random(), bmrng.uniform(20, 3000), bmrng.uniform(0, 6)),
                                          "square": "square %.2f %.1f %.2f" % (bmrng.random(), bmrng.uniform(20, 1000), bmrng.uniform(0, 6)),
                                          "noise": "noise %d %.2f" % (bmrng.randint(1, 99), bmrng.random() * 0.4),
                                          "dc": "dc %.2f" % bmrng.uniform(-0.5, 0.5)}[k]))
    for _ in range(n):
        r = bmrng.random()
        pick = bmrng.choice
        if r < 0.3: out.append("draw %d" % pick([16, 16, 33, 0, 250]))
        elif r < 0.38: out.append(pick(["display yt", "display xy"]))
        elif r < 0.44: out.append("tb %d" % bmrng.randint(0, 8))
        elif r < 0.5: out.append(pick(["zoom %g" % pick([1, 1, 1.19, 2, 4, 16, 64]), "persist %g" % pick([0, 0.1, 0.5, -1])]))
        elif r < 0.58: out.append(pick(["beam %s" % pick(["off", "subtle", "moderate", "high"]), "beamxy %d" % (bmrng.random() < 0.7),
                                        "beamyt %d" % (bmrng.random() < 0.6)]))
        elif r < 0.64: out.append(pick(["stack %d" % (bmrng.random() < 0.7), "name %.1f" % bmrng.uniform(0, 200),
                                        "canvas %d %d" % (bmrng.randint(200, 2000), bmrng.randint(150, 900)), "resize", "forget"]))
        elif r < 0.7: out.append(pick(["pair %d %d" % (bmrng.randint(0, 1), bmrng.randint(0, 1)),
                                       "figures %s" % pick(["none", "0,1;2,3", "0,1", "1,0;0,1"])]))
        elif r < 0.78: out.append(pick(["offset %d %.2f" % (bmrng.randint(0, 3), bmrng.uniform(-0.6, 0.6)),
                                        "fs %d %d" % (bmrng.randint(0, 3), pick([0, -6, -20])), "on %d %d" % (bmrng.randint(0, 3), bmrng.random() < 0.7)]))
        elif r < 0.86: out.append(pick(["pos %.2f" % bmrng.random(), "level %.2f" % bmrng.uniform(-0.8, 0.8), "trig %d" % bmrng.randint(0, 1),
                                        "edge %s" % pick(["rising", "falling"])]))
        elif r < 0.93: out.append(pick(["rot %.3f" % pick([0, 0, bmrng.uniform(-1, 1)]), "rotmod %.3f" % bmrng.uniform(-0.2, 0.2),
                                        "shaping %d" % (bmrng.random() < 0.8), "lanes %d" % (bmrng.random() < 0.3), "ms %d" % (bmrng.random() < 0.2)]))
        else: out.append(pick(["lag %.2f" % bmrng.uniform(0, 5), "lagoff", "lagoff", "filter lowpass %d 0" % bmrng.randint(200, 900), "filter off"]))
    return cprun(*out)
bmruns += [("random-%d" % i, bmfuzz(40)) for i in range(40)]
bmtext = "".join(t for _, t in bmruns)
bmjs, bmcpp = bmboth(bmtext, "beam.txt")
bmlines = [len(t.strip().split("\n")) - 2 for _, t in bmruns]
def bmslice(out, i):
    lines = out.strip().split("\n")
    start = sum(bmlines[:i])
    return "\n".join(lines[start:start + bmlines[i]])
for i, (name, _) in enumerate(bmruns):
    if name.startswith("random-"): continue
    d = kdiff(bmslice(bmjs, i), bmslice(bmcpp, i))
    check("%s: %d commands, the same grid" % (name, bmlines[i]), d is None, d or "")
bmbad = [n for i, (n, _) in enumerate(bmruns) if n.startswith("random-") and kdiff(bmslice(bmjs, i), bmslice(bmcpp, i))]
check("40 random sequences of 40 commands, the same grid", not bmbad, ", ".join(bmbad))
def bmdraws(name): return [l for l in bmslice(bmjs, next(i for i, (n, _) in enumerate(bmruns) if n == name)).split("\n") if l.startswith("draw ")]
def bmgrid(line): w = line.split(); i = w.index("grid"); return (float(w[i + 1]), float(w[i + 2]))
def bmref(line, key): w = line.split(); return float(w[w.index(key, w.index("refs")) + 1])
ci = bmdraws("circle")
check("a circle at 220 Hz lays the same grid with the beam on or off, and a fifth, which changes speed, lays less with it on",
      bmgrid(ci[0]) == bmgrid(ci[1]) and bmgrid(ci[2])[0] < bmgrid(ci[3])[0], " ".join(str(bmgrid(l)[0]) for l in ci))
tu = bmdraws("turn")
check("the walk turns a rack's pair as the capture turns a stereo pair, and either is a different picture from the line unturned",
      bmgrid(tu[1]) == bmgrid(tu[2]) and bmgrid(tu[0]) != bmgrid(tu[1]) and bmgrid(tu[4]) == bmgrid(tu[0]),
      " ".join(str(bmgrid(l)[0]) for l in tu))
st = bmdraws("stack")
def bmplot(line): w = line.split(); i = w.index("plot"); return float(w[i + 1])
check("stacked, the gutter is 44 pixels, the widest name and sixteen more, and never past 22 per cent of the screen, rounded to a pixel",
      [bmplot(l) for l in st[:5]] == [44, 57, 176, 44, 176], " ".join(str(bmplot(l)) for l in st))
an = bmdraws("anchor")
a = 1 - math.exp(-16 / 1000 / 0.5)
fresh = bmref(an[3], "xy")
check("the anchor moves a thirty-second of the way to a new figure in a frame, and starts afresh at the figure's own once forgotten",
      abs(bmref(an[1], "xy") - (bmref(an[0], "xy") + (fresh - bmref(an[0], "xy")) * a)) < 1e-12 and fresh != bmref(an[0], "xy")
      and abs(fresh + 20 - round((fresh + 20) / (50 / 64) - 0.5) * (50 / 64) - 25 / 64) < 1e-12,
      " ".join(str(bmref(l, "xy")) for l in an))
fi = bmdraws("figures")
check("two figures hold an anchor each, and figures naming a lane that is not there give way to the pair the menus chose",
      " xy1 " in fi[0] and bmgrid(fi[1]) == bmgrid(fi[2]) and bmgrid(fi[0]) != bmgrid(fi[2]) and bmgrid(fi[3]) != bmgrid(fi[2]),
      " ".join(str(bmgrid(l)[0]) for l in fi))
def bmnull(name, old, new, what):
    text = dict(bmruns)[name]
    assert old in text, old
    js, _ = bmboth(text.replace(old, new, 1))
    i = next(k for k, (n, _) in enumerate(bmruns) if n == name)
    check("and against " + what, kdiff(js, bmslice(bmcpp, i)) is not None)
bmnull("xy", "beam high", "beam subtle", "a softer beam")
bmnull("yt", "zoom 16", "zoom 15", "a zoom one step less")
bmnull("turn", "rot 0.125", "rot 0.126", "a turn a thousandth further")
bmnull("anchor", "draw 500", "draw 501", "a frame a millisecond longer")
check("and the comparison fails against the page's lines one command out of step",
      kdiff("\n".join(bmjs.strip().split("\n")[1:]), "\n".join(bmcpp.strip().split("\n")[:-1])) is not None)

print("\n--- the picture's sources ---")
# The page's phosphor grid, the beam's moments, the picture meter, the drawn
# pair's shape, the photocell and pictureStep, lifted by name, against
# scope/picture.h through the same commands. What the renderer would deposit
# is the run's own segments and polylines, so this is the arithmetic: what
# walks the beam is the next piece. A line a command: the grid's two sums
# and the roundness, and at each frame every value, raw and slewed, the
# meter and its verdict.
pcexe = build("picture_cpp")
def pcboth(text, name="picture_one.txt"):
    path = os.path.join(BUILD, name)
    with open(path, "w") as f: f.write(text)
    js = subprocess.run(["node", os.path.join(HERE, "tools", "picture_js.mjs"), path], check=True,
                        capture_output=True, text=True).stdout
    return js, subprocess.run([pcexe, path], check=True, capture_output=True, text=True).stdout
def pcrun(*commands): return "run\n%s\nend\n" % "\n".join(commands)
def pcellipse(cx, cy, rx, ry, n=48, turn=0.0):
    return "poly " + ";".join("%.4f,%.4f" % (cx + rx * math.cos(2 * math.pi * k / n + turn), cy + ry * math.sin(2 * math.pi * k / n + turn))
                              for k in range(n + 1))
def pcframes(count, elapsed=16, deposit=None):
    out = []
    for i in range(count):
        out.append("fade")
        if deposit: out.append(deposit(i))
        out.append("step %d" % elapsed)
    return out
PC = ["plot 40 30 600 450", "photo 1 0.5 0.5"]
pcruns = [
    # One segment: the cells it crosses, its moments, the reading beside it
    # and on it, and the bilinear reads moving smoothly across a cell edge.
    ("segment", pcrun("plot 40 30 600 450", "fade", "seg 40 30 640 480 1", "read 0.5 0.5", "read 0.51 0.5",
                      "seg 100 400 600 100 0.5", "read 0.25 0.25", *["read %.4f 0.5" % (0.49 + i * 0.002) for i in range(11)],
                      "seg -50 -50 900 900 1", "seg 340 255 340 255 1")),
    # Long segments, cut to the grid before they are walked: one straight
    # across from a million pixels out, then down, corner to corner, wholly
    # off to one side and to another, one leaving from the middle, the two
    # either side of where the cut begins, and ends that are not numbers or
    # are infinite; one lying along the graticule's top edge, which is on it.
    # Last, an end not a number across and infinite down, whose
    # length the language makes infinite rather than not a number - which
    # spoils the moments for the rest of the run, so it goes at the end.
    ("cut", pcrun("plot 40 30 600 450", "persist 0", "fade", "seg -1e6 255 1e6 255 1", "fade", "seg 340 -1e9 340 1e9 0.5", "seg -1e6 -1e6 1e6 1e6 1",
                  "seg -1e6 1000 -900 1000 1", "seg 2000 -5e5 2100 5e5 1", "seg 340 255 1e7 260 1", "fade", "seg 40 100 1239 100 1",
                  "seg 40 200 1241 200 1", "seg 340 255 NaN 255 1", "seg 340 255 Infinity 255 1", "seg Infinity 0 Infinity 10 1",
                  "seg -1e6 30 1e6 30 1", "seg 340 255 NaN Infinity 1")),
    # Segments far too long to walk whole - some 8.5e11 half cells, under the
    # bound where the cut part is walked afresh - across, down and corner to
    # corner: a walk that strays past the part on the grid never finishes.
    ("far", pcrun("plot 40 30 600 450", "persist 0", "fade", "seg -2e12 255 2e12 255 1", "seg 340 -1.5e12 340 1.5e12 1",
                  "seg -2e12 -1.5e12 2e12 1.5e12 0.5")),
    # A circle fading frame by frame, then infinite, then off, then a resize.
    ("fade", pcrun("plot 40 30 600 450", "persist 0.12", "fade", pcellipse(340, 255, 150, 150), "read 0.75 0.5",
                   *["fade" for _ in range(6)], "read 0.75 0.5", "persist -1", "fade", "fade", "persist 0.3", "fade",
                   "persist 0", "fade", pcellipse(340, 255, 150, 150), "persist 0.12", "fade 1")),
    # The beam's steps: a polyline shaded, each segment at its own level.
    ("steps", pcrun("plot 0 0 512 512", "fade", "poly 0,0;100,100;200,50;300,300;511,511 0,3,7,1", "read 0.2 0.2",
                    "poly 10,500;500,10 7")),
    # Roundness: a circle, an ellipse two to one, turned, and a line; and a
    # figure shrinking towards nothing, which fades rather than falling.
    ("round", pcrun("plot 0 0 400 400", "persist 0", "fade", pcellipse(200, 200, 120, 120), "fade",
                    pcellipse(200, 200, 160, 80), "fade", pcellipse(200, 200, 160, 80, turn=0.7), "fade",
                    "seg 20 20 380 380 1", *[x for r in (40, 10, 3, 1, 0.3) for x in ("fade", pcellipse(200, 200, r, r))])),
    # The photocell on a lit cell and a dark one, slewed at two swings a
    # second; off reads nothing, and so does the spectrogram.
    ("photo", pcrun(*PC, "persist -1", "fade", "seg 40 255 640 255 1", "pair ellipse 0.5 0.5 3 4096 0",
                    *["step 16" for _ in range(40)], "photo 1 0.5 0.1", *["step 33" for _ in range(20)],
                    "photo 0", "step 16", "photo 1", "spect 1", "step 16", "spect 0", "step 100", "step 0", "step -5")),
    # A still picture: change falls to nought, the verdict says settled, and
    # boredom rises at a quarter a second.
    ("settled", pcrun(*PC, "persist -1", "fade", pcellipse(340, 255, 120, 80), "pair ellipse 0.5 0.3 3 4096 0",
                      *["step 50" for _ in range(160)], "photo 0", "step 50", "photo 1", "step 50")),
    # A circle that keeps turning half its way round and back: it moves every
    # frame and keeps coming back - cycling; then one that never does.
    ("cycling", pcrun(*PC, "persist 0", "pair ellipse 0.5 0.3 3 4096 0",
                      *pcframes(200, 50, lambda i: pcellipse(340 + 120 * math.sin(i * 0.8), 255, 60, 40)))),
    ("wandering", pcrun(*PC, "persist 0", "pair ellipse 0.5 0.3 3 4096 0",
                        *pcframes(200, 50, lambda i: pcellipse(60 + (i * 37) % 520, 40 + (i * 53) % 380, 30 + i % 17, 20 + i % 11)))),
    # The screen full of ink, and a limiter held under six decibels: running away.
    ("running", pcrun(*PC, "persist -1", "fade", *["seg 40 %d 640 %d 1" % (30 + y, 30 + y) for y in range(0, 450, 4)],
                      "pair ellipse 0.5 0.3 3 4096 0", *["step 50" for _ in range(100)])),
    ("strained", pcrun(*PC, "persist 0.5", "pair ellipse 0.5 0.3 3 4096 0", "limit -8",
                       *pcframes(100, 50, lambda i: pcellipse(340 + 120 * math.sin(i * 1.3), 255, 60, 40)), "limit -2", "step 50")),
    # A figure whose whole path weighs less than the moments' floor reads
    # nought; a cell given more than full ink still counts as one.
    ("tiny", pcrun("plot 0 0 400 400", "fade", "poly 200,200;200.00000001,200;200.00000001,200.00000001;200,200.00000001;200,200",
                   *PC[1:], "pair ellipse 0.5 0.3 3 4096 0", "step 16", "seg 10 10 390 10 2", "step 16")),
    # Twenty seconds: a picture from the first two comes back after fifteen,
    # by when it has left the meter's memory; a picture held still and then
    # boredom let go and taken up again from nothing.
    ("long", pcrun(*PC, "persist 0", "pair ellipse 0.5 0.3 3 4096 0",
                   *pcframes(400, 50, lambda i: pcellipse(100, 100, 40, 40) if i < 40 or i >= 360
                             else pcellipse(150 + (i * 37) % 400, 100 + (i * 53) % 300, 30, 20)),
                   "photo 0", "step 50", "photo 1", "step 50")),
    # Frames a second apart, so the window holds few rows and the history
    # grows a snapshot a step; and frames 0.7 s apart that move and hold in
    # turn, so the window's median is between a moving frame and a still one.
    ("sparse", pcrun(*PC, "persist 0", "pair ellipse 0.5 0.3 3 4096 0",
                     *pcframes(16, 1000, lambda i: pcellipse(340 + 50 * math.sin(i), 255, 60, 40)),
                     *pcframes(30, 700, lambda i: pcellipse(340 + 100 * ((i // 2) % 2), 255, 60, 40)))),
    # The drawn pair: round each way, a line, through a gain, an offset, a
    # turn and a zoom that reaches the edge; no frame at all.
    ("shape", pcrun(*PC, "fade", "pair ellipse 0.5 0.3 3 4096 0", "step 16", "pair ellipse 0.5 0.3 3 4096 3.1416",
                    "step 16", "pair ellipse 0.5 0.5 3 4096 1.5708", "step 16", "view 2 0.5 0.1 -0.2 0.125 1.5", "step 16",
                    "pair ellipse 0.9 0.9 5 9000 0", "view 1 1 0 0 0 1.1", "step 16", "pair noise 7 0.4 3000", "step 16",
                    "pair ellipse 0.5 0.3 1 2 0", "step 16", "pair none", "step 16")),
]
pcrng = random.Random(104)
def pcfuzz(n):
    out = ["plot %d %d %d %d" % (pcrng.randint(0, 50), pcrng.randint(0, 50), pcrng.randint(100, 800), pcrng.randint(100, 600)),
           "photo 1 %.3f %.3f" % (pcrng.random(), pcrng.random()), "pair ellipse 0.5 0.3 3 4096 0"]
    for _ in range(n):
        r = pcrng.random()
        if r < 0.25: out.append("fade" + (" 1" if pcrng.random() < 0.03 else ""))
        elif r < 0.45: out.append("seg %.2f %.2f %.2f %.2f %.3f" % tuple(pcrng.uniform(-100, 900) for _ in range(4)) + (pcrng.random(),) if False else
                                  "seg %.2f %.2f %.2f %.2f %.3f" % (pcrng.uniform(-100, 900), pcrng.uniform(-100, 700), pcrng.uniform(-100, 900),
                                                                   pcrng.uniform(-100, 700), pcrng.random()))
        elif r < 0.55: out.append(pcellipse(pcrng.uniform(0, 800), pcrng.uniform(0, 600), pcrng.uniform(1, 300), pcrng.uniform(1, 300),
                                            pcrng.randint(3, 60), pcrng.random() * 6))
        elif r < 0.6:
            k = pcrng.randint(2, 8)
            out.append("poly " + ";".join("%.1f,%.1f" % (pcrng.uniform(0, 800), pcrng.uniform(0, 600)) for _ in range(k)) + " "
                       + ",".join(str(pcrng.randint(0, 7)) for _ in range(k - 1)))
        elif r < 0.63: out.append("read %.3f %.3f" % (pcrng.uniform(-0.1, 1.1), pcrng.uniform(-0.1, 1.1)))
        elif r < 0.66: out.append("persist %s" % pcrng.choice(["0", "-1", "0.04", "0.12", "0.3"]))
        elif r < 0.68: out.append("photo %d %.3f %.3f" % (pcrng.random() < 0.8, pcrng.random(), pcrng.random()))
        elif r < 0.7: out.append("spect %d" % (pcrng.random() < 0.3))
        elif r < 0.73: out.append(pcrng.choice(["pair ellipse %.2f %.2f %d %d %.3f" % (pcrng.uniform(0, 1), pcrng.uniform(0, 1), pcrng.randint(1, 9),
                                                pcrng.choice([2, 100, 4096, 5000]), pcrng.uniform(0, 6.3)),
                                                "pair noise %d %.2f %d" % (pcrng.randint(1, 99), pcrng.random(), pcrng.choice([50, 3000])), "pair none"]))
        elif r < 0.75: out.append("view %.2f %.2f %.2f %.2f %.3f %.2f" % (pcrng.uniform(0.2, 3), pcrng.uniform(0.2, 3), pcrng.uniform(-0.3, 0.3),
                                  pcrng.uniform(-0.3, 0.3), pcrng.choice([0, 0, pcrng.uniform(-1, 1)]), pcrng.uniform(0.5, 4)))
        elif r < 0.77: out.append("limit %.1f" % pcrng.choice([0, -2, -7, -12]))
        else: out.append("step %d" % pcrng.choice([16, 16, 33, 50, 100, 250, 0]))
    return pcrun(*out)
pcruns += [("random-%d" % i, pcfuzz(200)) for i in range(30)]
pctext = "".join(t for _, t in pcruns)
pcjs, pccpp = pcboth(pctext, "picture.txt")
pclines = [len(t.strip().split("\n")) - 2 for _, t in pcruns]
def pcslice(out, i):
    lines = out.strip().split("\n")
    start = sum(pclines[:i])
    return "\n".join(lines[start:start + pclines[i]])
for i, (name, _) in enumerate(pcruns):
    if name.startswith("random-"): continue
    d = kdiff(pcslice(pcjs, i), pcslice(pccpp, i))
    check("%s: %d commands, the same grid, moments, meter and sources" % (name, pclines[i]), d is None, d or "")
pcbad = [n for i, (n, _) in enumerate(pcruns) if n.startswith("random-") and kdiff(pcslice(pcjs, i), pcslice(pccpp, i))]
check("30 random sequences of 200 commands, the same grid, moments, meter and sources", not pcbad, ", ".join(pcbad))
# The compiled core's picture engine (5d), the one the site now runs, through
# the same runs: made as the page makes it, from the module the page carries,
# and driven through the page's own wrappers. Its output is the page's to the
# character, which is stronger than the tolerance and is what it gave.
def pcwasm(path):
    return subprocess.run(["node", os.path.join(HERE, "tools", "picture_js.mjs"), path], env=dict(os.environ, CORE="wasm"),
                          check=True, capture_output=True, text=True).stdout
pcwa = pcwasm(os.path.join(BUILD, "picture.txt"))
check("the site's picture engine, compiled, through every run: the page's output to the character, and the core's to %g" % TOL,
      pcwa == pcjs and kdiff(pcwa, pccpp) is None,
      "%d lines; first difference from the page %r" % (len(pcwa.split("\n")),
       next((i for i, (x, y) in enumerate(zip(pcwa.split("\n"), pcjs.split("\n"))) if x != y), None)))
# The null: the runs with every persistence a hundredth more, which the
# comparison has to see.
pcbent = os.path.join(BUILD, "picture_bent.txt")
with open(pcbent, "w") as f:
    f.write(re.sub(r"^persist ([0-9.]+)$", lambda m: "persist %r" % (float(m.group(1)) + 0.01) if float(m.group(1)) > 0 else m.group(0),
                   pctext, flags=re.M))
check("and the comparison fails against the runs with every persistence a hundredth more", kdiff(pcwasm(pcbent), pcjs) is not None)
def pcout(name): return pcslice(pcjs, next(i for i, (n, _) in enumerate(pcruns) if n == name)).split("\n")
def pcfield(line, word, k=0): w = line.split(); return w[w.index(word) + 1 + k]
pcsteps = lambda name: [l for l in pcout(name) if l.startswith("step")]
check("the verdicts are each reached: settled, cycling, wandering and running away, twice",
      pcfield(pcsteps("settled")[159], "meter", 5) == "settled" and pcfield(pcsteps("cycling")[-1], "meter", 5) == "cycling"
      and pcfield(pcsteps("wandering")[-1], "meter", 5) == "wandering" and pcfield(pcsteps("running")[-1], "meter", 5) == "running"
      and pcfield(pcsteps("strained")[-2], "meter", 5) == "running",
      " ".join(pcfield(pcsteps(n)[159 if n == "settled" else -1], "meter", 5) for n in ("settled", "cycling", "wandering", "running")))
ro = [float(pcfield(l, "round")) for l in pcout("round")]
check("roundness reads near one for a circle, under two thirds for two to one at any turn, nought for a line, and fades as a figure shrinks",
      ro[3] > 0.9 and 0.5 < ro[5] < 0.65 and abs(ro[7] - ro[5]) < 0.02 and ro[9] < 1e-6
      and ro[11] > ro[13] > ro[15] > ro[17] > ro[19] >= 0, repr([round(x, 3) for x in ro]))
ph = [float(pcfield(l, "photo", 1)) for l in pcsteps("photo")]
check("the photocell climbs at two swings a second to what is under it, falls on a dark cell, and reads nothing off or on the spectrogram",
      abs(ph[0] - 0.032) < 1e-12 and ph[39] > 0.3 and ph[59] < ph[39] and ph[60] == 0 and ph[61] == 0, repr([round(x, 3) for x in ph[:3] + ph[38:41] + ph[58:62]]))
bo = [float(pcfield(l, "raw", 6)) for l in pcsteps("settled")][:160]
bo2 = [float(pcfield(l, "raw", 6)) for l in pcsteps("settled")][160:]
check("and the photocell turned off lets boredom go: on again, it starts from nothing rather than where it was",
      bo[-1] > 0.5 and bo2 == [0.0, 0.0], repr(bo2))
check("boredom rises while the picture is still, toward eight tenths over ten seconds of stillness",
      bo[-1] > 0.5 and all(b2 >= b1 for b1, b2 in zip(bo[10:], bo[11:])), repr(round(bo[-1], 3)))
sh = [(float(pcfield(l, "shape")), float(pcfield(l, "shape", 1))) for l in pcsteps("shape")]
check("the drawn pair: anticlockwise one way and clockwise the other, a line nought, and the edge reached when zoomed",
      sh[0][0] > 0.5 and sh[1][0] < -0.5 and abs(sh[2][0]) < 0.05 and sh[4][1] > 0.1 and sh[7] == (0.0, 0.0), repr(sh))
def pcnull(name, old, new, what):
    text = dict(pcruns)[name]
    assert old in text, old
    js, _ = pcboth(text.replace(old, new, 1))
    i = next(k for k, (n, _) in enumerate(pcruns) if n == name)
    check("and against " + what, kdiff(js, pcslice(pccpp, i)) is not None)
pcnull("segment", "seg 100 400 600 100 0.5", "seg 100 400 600 101 0.5", "a segment a pixel lower at one end")
cu = pcslice(pcjs, next(i for i, (n, _) in enumerate(pcruns) if n == "cut")).split("\n")
def cugrid(line): w = line.split(); return float(w[w.index("grid") + 2])
check("a segment from a million pixels off one side to a million off the other lights all 64 cells of its row, and no more",
      cugrid(cu[3]) == 64, cu[3][:80])
check("either side of where the cut begins, a segment from the graticule's left edge lights the same 64 cells",
      cugrid(cu[12]) - cugrid(cu[11]) == 64 and cugrid(cu[11]) == 64, "%s %s" % (cugrid(cu[11]), cugrid(cu[12])))
# The cut is there for the time a long segment takes, and must not change what
# it lights: every run above through a copy of the page with the cut taken
# out, line for line the same. A first cut walked the cut part afresh, at a
# different phase, and the corner-to-corner stroke of the first run lit other
# cells - which parity could not see, since both sides had changed together.
with open(os.path.join(HERE, "..", "..", "web", "scope.html")) as f: whole = f.read()
assert whole.count("  if (steps > 4 * N) {") == 1
uncut = os.path.join(BUILD, "scope_uncut.html")
with open(uncut, "w") as f: f.write(whole.replace("  if (steps > 4 * N) {", "  if (false) {"))
# Every run but the one too long to walk whole.
near = [i for i, (n, _) in enumerate(pcruns) if n != "far"]
with open(os.path.join(BUILD, "picture_near.txt"), "w") as f: f.write("".join(pcruns[i][1] for i in near))
pcuncut = subprocess.run(["node", os.path.join(HERE, "tools", "picture_js.mjs"), os.path.join(BUILD, "picture_near.txt")], check=True,
                         capture_output=True, text=True, timeout=600, env=dict(os.environ, SCOPE_PAGE=uncut)).stdout
pcnear = "\n".join(pcslice(pcjs, i) for i in near)
check("every picture run lays the same grid with the long segments cut as walked whole, to the last bit",
      pcuncut.strip() == pcnear.strip(), kdiff(pcnear, pcuncut) or "")
pcnull("fade", "persist 0.3", "persist 0.31", "a persistence a hundredth longer")
pcnull("photo", "photo 1 0.5 0.1", "photo 1 0.5 0.497", "the reticle at the edge of the line rather than off it")
pcnull("strained", "limit -8", "limit -5", "a limiter under six decibels")
check("and the comparison fails against the page's lines one command out of step",
      kdiff("\n".join(pcjs.strip().split("\n")[1:]), "\n".join(pccpp.strip().split("\n")[:-1])) is not None)

print("\n--- the hearing ---")
def midi_hz(note): return 440 * 2 ** ((note - 69) / 12)
# The page's hearing - a window of the sound analysed once a frame into a
# pitch, a brightness, four bands, a width, a flux and an onset - lifted by
# name, against scope::HearingSources, through the same commands. A line a
# command: every value it keeps, the onset's state, how many times the
# routings were touched, and each source's loop flag and reach.
hexe = build("hearing_cpp")
def hboth(text, name="hearing_one.txt"):
    path = os.path.join(BUILD, name)
    with open(path, "w") as f: f.write(text)
    js = subprocess.run(["node", os.path.join(HERE, "tools", "hearing_js.mjs"), path], check=True,
                        capture_output=True, text=True).stdout
    return js, subprocess.run([hexe, path], check=True, capture_output=True, text=True).stdout
def hrun(*commands): return "run\n%s\nend\n" % "\n".join(commands)
def hframes(n, ms=16): return ["frame %r" % ms] * n
hruns = [
    # A full-scale sine inside each band in turn: that band reads near one, the others near nought.
    # Each held 100 frames: the bands release on 250 ms, and the last band takes that long to let go.
    ("hear-bands", hrun(*sum((["clear", "tone 0 %r 1 0" % hz, *hframes(100)] for hz in (60, 400, 2000, 8000)), []))),
    # 220 Hz and nothing held: the estimator names it, every other frame, and the pitch slews there at four a second.
    ("hear-pitch", hrun("tone 0 220 0.5 0", *hframes(30), "clear", "tone 0 440 0.5 0", *hframes(30))),
    # A held key outranks what is heard; a chord's lowest note is the key; let go, the estimator again.
    ("hear-held", hrun("tone 0 220 0.5 0", "held 69", *hframes(20), "held 64 57 72", *hframes(20), "held -", *hframes(20))),
    # Silence: the pitch, the brightness and the width hold; the bands and the flux fall away.
    ("hear-floor", hrun("tone 0 330 0.5 0", "tone 1 330 0.5 1", *hframes(20), "clear", *hframes(80))),
    # The width: one channel the same, inverted, a quarter-cycle on, the same lane twice, and one lane only.
    # Forty frames each: from one to minus one is half a second at the slew's four a second.
    ("hear-width", hrun("tone 0 300 0.5 0", "tone 1 300 0.5 0", *hframes(15), "clear", "tone 0 300 0.5 0", "tone 1 300 0.5 3.141592653589793",
                        *hframes(40), "clear", "tone 0 300 0.5 0", "tone 1 300 0.5 1.5707963267948966", *hframes(40), "xy 1 1", *hframes(40),
                        "xy 0 1", "lanes 1", *hframes(40), "lanes 2", "clear", "tone 0 300 0.5 0", "xy 1 1", *hframes(10))),
    # An onset: a note out of silence, starting in the window's newer half, fires once; a note stopping does not; one 64 ms
    # after the last is held back by the gap, the next, 128 ms after, fires, and two more exactly 80 ms apart both fire.
    ("hear-onset", hrun("at 0", "frame 16", "tone 0 500 0.5 0", "gap first", "at 16", "frame 16", "gap none", *sum((["at %d" % (32 + 16 * k), "frame 16"] for k in range(8)), []),
                        "gap second", "at 200", "frame 16", "clear", "at 216", "frame 16", "tone 0 700 0.5 0", "gap first", "at 232", "frame 16",
                        "gap none", "at 260", "frame 16", "clear", "at 280", "frame 16", "tone 0 900 0.5 0", "gap first", "at 296", "frame 16",
                        "gap none", "at 320", "frame 16", "clear", "at 340", "frame 16", "tone 0 1100 0.5 0", "gap first", "at 360", "frame 16",
                        "gap none", "at 400", "frame 16", "clear", "at 420", "frame 16", "tone 0 1300 0.5 0", "gap first", "at 440", "frame 16",
                        "gap none", "clear", "at 470", "frame 16", "tone 0 1700 0.5 0", "gap first", "at 520", "frame 16", "gap none", "at 540", "frame 16")),
    # What is heard stops being the generator and starts again: the loop flag and the reach follow, and the routes are touched each time.
    ("hear-gen", hrun("tone 0 250 0.5 0", "frame 16", "gen 0", "frame 16", "frame 16", "gen 1", "frame 16", "running 0", "gen 0", "frame 16",
                      "running 1", "frame 16")),
    # The lane the trigger watches, and one there is not, which reads the first.
    ("hear-trig", hrun("tone 0 200 0.5 0", "tone 1 3000 0.5 0", *hframes(10), "trig 1", *hframes(10), "trig 5", *hframes(10))),
    # The estimator's corners. A window of 256 is too short for the doubling, so the dip's own parabola is the answer;
    # a 376 Hz period runs to the end of its range, which is no answer; and 355 Hz under noise never dips under the
    # threshold and is deepest at the end, which is none either. An offset with a trace of tone on it: the mean comes
    # off and what is left is too little to measure. A tone quiet enough that its spectrum sums under a half, still over
    # the floor. Two bars of an organ, 8' and 1', whose near-repeat dips before the real period. Noise alone. And 32768
    # samples of a tone under noise, where the newest 16384 is not trusted and the whole window, decimated by twos -
    # averaged, which halves the noise - is. The first three eighths of the window silent: the halves' energies four to
    # one apart, which is not steady, so the estimator is not asked. (A quarter is two to one, and whether that is under
    # two is a matter of where the cycles fall.)
    ("hear-estimator", hrun("len 256", "tone 0 500 0.5 0", *hframes(6), "clear", "tone 0 376 0.5 0", *hframes(6), "clear",
                            "tone 0 355 0.5 0", "noise 0 5 0.2", *hframes(8), "len 4096", "clear",
                            "tone 0 0 0.5 1.5707963267948966", "tone 0 300 0.00003 0", *hframes(6), "len 256", "clear", "tone 0 700 0.0015 0",
                            *hframes(6), "len 4096", "clear", "tone 0 261.63 0.4 0", "tone 0 2093 0.4 0", *hframes(6), "clear", "noise 0 9 0.5",
                            *hframes(6), "len 256", *hframes(6), "len 32768", "clear", "tone 0 150 0.3 0", "noise 0 4 0.3", *hframes(6),
                            "frame -16", "frame 16", "len 4096", "clear", "tone 0 300 0.5 0", "gap early", *hframes(6), "gap none")),
    # Windows too short to hear, the shortest heard, and long ones; the longest past the estimator's 16384, decimated.
    ("hear-lengths", hrun("tone 0 180 0.4 0", "noise 0 3 0.3", "len 128", *hframes(3), "len 256", *hframes(6), "len 1024", *hframes(6),
                          "len 32768", *hframes(6), "len 4096", *hframes(6))),
]
def hfuzz(n):
    out = []
    for _ in range(n):
        t, cmds = 0, ["lanes %d" % hrng.choice([1, 2, 2]), "len %d" % hrng.choice([256, 1024, 4096, 4096, 8192])]
        for _ in range(hrng.randint(15, 45)):
            t += hrng.choice([0, 8, 16, 17, 33, 80, 120])
            cmds.append("at %d" % t)
            r = hrng.random()
            if r < 0.45: cmds.append("frame %r" % hrng.choice([0, 8, 16, 16.7, 33, 100, -16]))
            elif r < 0.6: cmds.append("tone %d %r %r %r" % (hrng.randint(0, 1), hrng.choice([40, 110, 220, 261.6256, 523, 1500, 5000, 11000]) * hrng.choice([1, 1.01]),
                                                       hrng.choice([0, 0.0005, 0.05, 0.5, 1]), hrng.choice([0, 1, 3.14])))
            elif r < 0.66: cmds.append("noise %d %d %r" % (hrng.randint(0, 1), hrng.randint(1, 50), hrng.choice([0.01, 0.3, 1])))
            elif r < 0.72: cmds.append("clear")
            elif r < 0.78: cmds.append("gap %s" % hrng.choice(["none", "none", "first", "second"]))
            elif r < 0.84: cmds.append("held %s" % hrng.choice(["-", "-", "60", "45 52", "81"]))
            elif r < 0.88: cmds.append("gen %d" % hrng.randint(0, 1))
            elif r < 0.91: cmds.append("running %d" % hrng.randint(0, 1))
            elif r < 0.95: cmds.append("trig %d" % hrng.randint(0, 2))
            else: cmds.append("xy %d %d" % (hrng.randint(0, 2), hrng.randint(0, 2)))
        out.append(hrun(*cmds))
    return out
hrng = random.Random(53)
hfuzzed = hfuzz(100)
htext = "".join(r for _, r in hruns) + "".join(hfuzzed)
hjs, hcpp = hboth(htext, "hearing.txt")
hd = kdiff(hjs, hcpp)
check("%d runs of the hearing, %d of them random, are the page's line for line" % (len(hruns) + len(hfuzzed), len(hfuzzed)),
      hd is None and len(hjs.split("\n")) > 1500, hd or "%d lines" % len(hjs.split("\n")))
def hout(name):
    js, _ = hboth(dict(hruns)[name])
    return js.strip().split("\n")
def hfield(line, name, count=1):
    t = line.split(" | ")[-1].split()
    i = t.index(name)
    return t[i + 1] if count == 1 else t[i + 1:i + 1 + count]
L = [l for l in hout("hear-bands") if l.startswith("frame")]
reads = [[float(x) for x in hfield(L[100 * b + 99], "bands", 4)] for b in range(4)]
check("a full-scale sine inside a band reads near one there and near nought in the others, for each of the four",
      all(reads[b][b] > 0.95 and all(reads[b][o] < 0.05 for o in range(4) if o != b) for b in range(4)),
      str([[round(x, 3) for x in r] for r in reads]))
L = [l for l in hout("hear-pitch") if l.startswith("frame")]
want220, want440 = math.log2(220 / 261.6256) / 2, math.log2(440 / 261.6256) / 2
check("220 Hz with nothing held is named, the pitch moving 0.064 a frame of 16 ms towards it, and 440 Hz an octave up",
      abs(float(hfield(L[0], "pitch")) - (-0.064)) < 1e-12 and abs(float(hfield(L[29], "pitch")) - want220) < 1e-3
      and abs(float(hfield(L[59], "pitch")) - want440) < 1e-3 and hfield(L[0], "frame") == "1",
      "%s, %s, %s" % (hfield(L[0], "pitch"), hfield(L[29], "pitch"), hfield(L[59], "pitch")))
L = [l for l in hout("hear-held") if l.startswith("frame")]
check("a held key outranks what is heard, a chord's lowest note is the key, and let go the estimator names the tone again",
      abs(float(hfield(L[19], "want")) - math.log2(440 / 261.6256) / 2) < 1e-12
      and abs(float(hfield(L[39], "want")) - math.log2(220 / 261.6256) / 2) < 1e-4 and abs(float(hfield(L[39], "want")) - math.log2(midi_hz(57) / 261.6256) / 2) < 1e-12
      and abs(float(hfield(L[59], "want")) - want220) < 1e-4, "%s, %s, %s" % (hfield(L[19], "want"), hfield(L[39], "want"), hfield(L[59], "want")))
L = [l for l in hout("hear-floor") if l.startswith("frame")]
check("in silence the pitch, the brightness and the width hold, and the bands and the flux fall away",
      hfield(L[19], "pitch") == hfield(L[-1], "pitch") and hfield(L[19], "bright") == hfield(L[-1], "bright")
      and hfield(L[19], "width") == hfield(L[-1], "width") and float(hfield(L[-1], "bands", 4)[1]) < 0.05 * float(hfield(L[19], "bands", 4)[1]),
      "pitch %s, then %s; band %s, then %s" % (hfield(L[19], "pitch"), hfield(L[-1], "pitch"), hfield(L[19], "bands", 4)[1], hfield(L[-1], "bands", 4)[1]))
L = [l for l in hout("hear-width") if l.startswith("frame")]
widths = [float(hfield(L[i], "width")) for i in (14, 54, 94, 134, 174)]
check("the width reads one for two channels alike, minus one for one inverted, nought a quarter-cycle on, one for one lane twice or one lane only",
      abs(widths[0] - 1) < 1e-6 and abs(widths[1] + 1) < 1e-3 and abs(widths[2]) < 0.02 and abs(widths[3] - 1) < 1e-9 and abs(widths[4] - 1) < 1e-9,
      str([round(w, 4) for w in widths]))
L = hout("hear-onset")
counts = [int(hfield(l, "onset")) for l in L if l.startswith("frame")]
check("a note out of silence fires the onset once; a note stopping does not; none within 80 ms of the last; and exactly 80 is allowed",
      counts[1] == 1 and counts[2:10] == [1] * 8 and counts[10] == 1 and counts[12] == 2 and counts[15] == 2 and counts[16] == 2
      and counts[18] == 3 and counts[19] == 3 and counts[21] == 4 and counts[23] == 5,
      str(counts))
L = hout("hear-gen")
src = lambda l: hfield(l, "sources", 9)
check("hearing the generator, every source is a loop with the picture's reach and the onset a loop; not, none are; the routes touched at each change",
      src(L[1])[0] == "1/0.50000000000000000" and src(L[1])[8] == "1/0.0000000000000000" and src(L[3])[0] == "0/0.0000000000000000"
      and hfield(L[1], "touched") == "1" and hfield(L[3], "touched") == "2" and hfield(L[6], "touched") == "3" and hfield(L[8], "touched") == "3"
      and src(L[8])[0] == "1/0.50000000000000000", "%s %s, touched %s %s %s %s" % (src(L[1])[0], src(L[3])[0], hfield(L[1], "touched"),
                                                                                   hfield(L[3], "touched"), hfield(L[6], "touched"), hfield(L[8], "touched")))
L = [l for l in hout("hear-trig") if l.startswith("frame")]
b0, b1, b2 = (float(hfield(L[i], "bright")) for i in (9, 19, 29))
check("the brightness follows the lane the trigger watches, and a lane that is not there reads the first",
      b1 > b0 + 0.1 and b2 < b1 - 0.1, "%.3f, %.3f, %.3f" % (b0, b1, b2))
L = [l for l in hout("hear-lengths") if l.startswith("frame")]
check("a window under 256 samples is not heard, 256 is, and 32768, past the estimator's window, is too",
      hfield(L[2], "frame") == "0" and hfield(L[3], "frame") == "1" and int(hfield(L[20], "frame")) > int(hfield(L[14], "frame")),
      "%s, %s, %s" % (hfield(L[2], "frame"), hfield(L[3], "frame"), hfield(L[20], "frame")))
def hnull(what, name, old, new):
    text = dict(hruns)[name]
    assert text.count(old) >= 1, old
    js, _ = hboth(text.replace(old, new, 1))
    _, cpp = hboth(text)
    check("and against " + what, kdiff(js, cpp) is not None)
hnull("a tone a cent sharp", "hear-pitch", "tone 0 220 0.5 0", "tone 0 220.127 0.5 0")
hnull("the other key held", "hear-held", "held 69", "held 70")
hnull("an onset a frame later", "hear-onset", "at 16\nframe 16\ngap none", "at 17\nframe 16\ngap none")
hnull("the generator heard throughout", "hear-gen", "gen 0\nframe 16", "gen 1\nframe 16")
check("and the comparison fails against the page's lines one command out of step",
      kdiff("\n".join(hjs.split("\n")[1:]), "\n".join(hcpp.split("\n")[:-1])) is not None)

print("\n--- the score and MIDI out ---")
# The page's score, its MIDI out and the crossings' and pluck's notes, on its
# bar, lifted by name, and scope's on a scope::Clock, through the same
# commands. A line a command: what was struck and every byte sent, then the
# playhead, the chord, what is sounding, the rate limit's count, and the
# note-offs due. The grid is the run's: the picture's, in the page, until
# stage 4.
sexe = build("score_cpp")
def sboth(text, name="score_one.txt"):
    path = os.path.join(BUILD, name)
    with open(path, "w") as f: f.write(text)
    js = subprocess.run(["node", os.path.join(HERE, "tools", "score_js.mjs"), path], check=True,
                        capture_output=True, text=True).stdout
    return js, subprocess.run([sexe, path], check=True, capture_output=True, text=True).stdout
def srun(*commands): return "run\n%s\nend\n" % "\n".join(commands)
def frames_at(start, stop, every): return ["at %r" % t if i == 0 else "frame" for t in range(start, stop, every) for i in (0, 1)]
sruns = [
    # One cell lit a column: the bottom row is the lowest pitch of the key, the top the highest, and a dim one is no note.
    ("score-rows", srun("port 1 0", "key 2 major", "cell 63 0 0.9", "cell 0 1 0.8", "cell 31 2 0.7", "cell 40 3 0.1",
                        "cell 40 4 0.15", "cell 10 5 0.5", "cell 12 5 0.6", "cell 50 5 0.4", "cell 60 5 0.3",
                        "score on 1/16 2 48 2", *frames_at(0, 800, 20))),
    # A step every sixteenth at 120; a frame two steps late plays only the newest.
    ("score-steps", srun("grid 3 0.4", "score on 1/16 3 48 3", "at 0", "frame", "at 126", "frame", "at 251", "frame",
                         "at 520", "frame", "at 530", "frame", "tempo 60", "at 700", "frame", "at 1100", "frame")),
    # Stop lets go and stands; Start brings the playhead back to the first column; the scope stopped plays nothing.
    ("score-stop", srun("port 1 3", "grid 5 0.5", "score on 1/8 2 36 4", *frames_at(0, 1300, 50), "stop", *frames_at(1300, 1500, 50),
                        "start", *frames_at(1500, 1800, 50), "running 0", *frames_at(1800, 2000, 50), "running 1",
                        *frames_at(2000, 2200, 50), "score off 1/8 2 36 4", "frame")),
    # Equal brightness in three bands and two voices: the lower pitches win the tie.
    ("score-ties", srun("cell 60 0 0.5", "cell 40 0 0.5", "cell 20 0 0.5", "score on 1/16 2 48 1", "at 0", "frame")),
    # The bar's one leaves the chord sounding with the playhead reset; the scope stopped then still lets it go.
    ("score-anchor", srun("port 1 0", "grid 4 0.5", "score on 1/16 3 48 2", "at 0", "frame", "at 60", "start", "running 0",
                          "frame", "running 1", "at 70", "frame")),
    # Under a MIDI clock the bar adds a twenty-fourth a tick, and six of them come to 0.24999999999999997: the step is
    # due on that tick all the same. Just after a MIDI Start the bar is a tick short of nought, and nothing plays.
    ("score-midi", srun("port 1 0", "grid 9 0.5", "score on 1/16 2 48 2", "at 0", "midistart", "frame",
                        *sum((["at %r" % (k * 20.833), "tick", "frame"] for k in range(1, 40)), []))),
    # Note-offs due on the frame's own millisecond go on it.
    ("offs-exact", srun("port 1 0", "cross 1 60 67", "at 1000", "counts 1 0", "frame", "at 1100", "frame",
                        "at 2000", "pluck 0.5", "at 2150", "frame")),
    # Forty note-ons a second and no more; the note-offs always go.
    ("out-rate", srun("port 1 0", *sum((["at %d" % (t * 20), "pluck 0.5", "frame"] for t in range(60)), []), "at 2000", "frame",
                      *sum((["at %d" % (2000 + t * 30), "pluck 0.7"] for t in range(10)), []))),
    # A note already sounding is ended first; a new port or channel lets everything go on the old one first.
    ("out-notes", srun("port 1 5", "pluckNote 64", "at 0", "pluck 0.3", "at 50", "pluck 1", "at 60", "port 1 6", "pluck 0.01",
                       "at 300", "frame", "port 0 0", "pluck 0.9", "panic")),
    # A crossing's count gone up is a note, ended a tenth of a second on; down - a new generator - is not.
    ("crossings", srun("port 1 0", "cross 1 60 67", "at 0", "counts 1 0", "frame", "at 50", "counts 3 2", "frame", "at 120", "frame",
                       "at 160", "frame", "counts 0 0", "frame", "counts 1 1", "cross 0 60 67", "frame", "counts 2 2", "frame",
                       "cross 1 72 74", "at 400", "frame", "at 600", "frame")),
]
def sfuzz(n):
    out = []
    for _ in range(n):
        t, cmds = 0, []
        for _ in range(srng.randint(30, 100)):
            t += srng.choice([0, 5, 16, 33, 60, 125, 250, 400])
            cmds.append("at %d" % t)
            r = srng.random()
            if r < 0.4: cmds.append("frame")
            elif r < 0.5: cmds.append("pluck %r" % srng.choice([0.2, 0.5, 1, 1.4, -0.3]))
            elif r < 0.56: cmds.append("score %s %s %s %s %s" % (srng.choice(["on", "on", "off"]), srng.choice(["1/16", "1/8", "1/4", "x"]),
                                                              srng.choice(["1", "2", "4", "0", "-1", "-2"]), srng.choice(["36", "48", "60"]), srng.choice(["1", "2", "3", "4"])))
            elif r < 0.62: cmds.append("grid %d %r" % (srng.randint(1, 99), srng.choice([0.05, 0.2, 0.6])))
            elif r < 0.66: cmds.append("key %d %s" % (srng.randint(0, 11), srng.choice(["chromatic", "major", "minorpent", "whole"])))
            elif r < 0.71: cmds.append("counts %d %d" % (srng.randint(0, 6), srng.randint(0, 6)))
            elif r < 0.74: cmds.append("cross %d %d %d" % (srng.randint(0, 1), srng.randint(48, 72), srng.randint(48, 72)))
            elif r < 0.78: cmds.append("port %d %d" % (srng.randint(0, 1), srng.randint(0, 15)))
            elif r < 0.81: cmds.append(srng.choice(["start", "stop", "midistart", "tick", "tick"]))
            elif r < 0.84: cmds.append("tempo %d" % srng.choice([60, 120, 180, 300]))
            elif r < 0.87: cmds.append("running %d" % srng.randint(0, 1))
            elif r < 0.9: cmds.append("pluckNote %d" % srng.randint(36, 84))
            elif r < 0.92: cmds.append("panic")
            else: cmds.append("cell %d %d %r" % (srng.randint(0, 63), srng.randint(0, 63), srng.choice([0.1, 0.15, 0.5, 1])))
        out.append(srun(*cmds))
    return out
srng = random.Random(43)
sfuzzed = sfuzz(50)
stext = "".join(r for _, r in sruns) + "".join(sfuzzed)
sjs, scpp = sboth(stext, "score.txt")
sd = kdiff(sjs, scpp)
check("%d runs of the score and the out, %d of them random, are the page's line for line" % (len(sruns) + len(sfuzzed), len(sfuzzed)),
      sd is None and len(sjs.split("\n")) > 3000, sd or "")
def sout(name):
    js, _ = sboth(dict(sruns)[name])
    return js.strip().split("\n")
def sfield(line, name):
    t = line.split(" | ")[-1].split()
    return t[t.index(name) + 1]
def chord(line): return [int(x.split("/")[0]) for x in sfield(line, "notes").split("+")] if sfield(line, "notes") != "-" else []
L = sout("score-rows")
cols = {}
for l in L:
    if l.startswith("frame") and sfield(l, "col") not in cols: cols[sfield(l, "col")] = chord(l)
# D major from 48 over two octaves: 49 50 52 54 55 57 59 61 62 64 66 67 69 71 - fourteen pitches, the bottom
# row the lowest. Row r is band floor((63 - r) * 14 / 64): row 31 is band 7 (61), row 40 band 5 (57).
check("a column's bottom row is the key's lowest pitch and its top row the highest; under the floor is no note, at it is",
      cols.get("0") == [49] and cols.get("1") == [71] and cols.get("2") == [61] and cols.get("3") == [] and cols.get("4") == [57],
      str(cols))
# Rows 10 and 12 share band 11 (67), at 0.6; row 50 is band 2 (52), at 0.4; row 60 band 0 (49), at 0.3; two voices.
check("the brightest few over the floor are the chord, loudest first, as many as the voices, a band as bright as its brightest row",
      cols.get("5") == [67, 52], str(cols.get("5")))
L = sout("score-steps")
fl = [l for l in L if l.startswith("frame")]
check("a step every sixteenth at 120, and a frame two steps late plays only the newest: no flam",
      [int(sfield(l, "col")) for l in fl[:5]] == [0, 1, 2, 4, 4] and sfield(fl[3], "steps") == "4" and sfield(fl[4], "steps") == "4",
      str([(sfield(l, "col"), sfield(l, "steps")) for l in fl[:5]]))
L = sout("score-stop")
stop = next(l for l in L if l.startswith("stop"))
start_i = next(i for i, l in enumerate(L) if l.startswith("start"))
first_after = next(l for l in L[start_i:] if l.startswith("frame"))
run0 = next(i for i, l in enumerate(L) if l.startswith("running"))
check("Stop lets the chord go; Start puts the playhead back on the first column; the scope stopped lets go and plays nothing",
      stop.count("send 131,") >= 1 and sfield(stop, "notes") == "-" and sfield(first_after, "col") == "0"
      and all(sfield(l, "col") == "-1" for l in L[run0 + 2:run0 + 9] if l.startswith("frame")),
      "%s | %s" % (stop[:80], sfield(first_after, "col")))
L = sout("score-ties")
check("three bands as bright as each other and two voices: the lower two pitches, in the order of the key",
      chord(L[5]) == [48, 52], L[5][-160:])
L = sout("score-anchor")
check("the bar's one leaves the chord sounding and the playhead back before the first step; the scope then stopped lets it go",
      sfield(L[6], "last") == "-1" and chord(L[6]) == [62, 60, 65] and "send 144" not in L[6]
      and "send 128,62,0 :: send 128,60,0 :: send 128,65,0" in L[8] and sfield(L[8], "notes") == "-"
      and sfield(L[11], "col") == "0", "%s | %s" % (L[6][:60], L[8][:80]))
L = sout("score-midi")
# Line 3 + 3k is the k-th tick's "at", then the tick, then the frame.
check("after a MIDI Start nothing plays until the clock's next tick, which is the one; the seventh tick, six twenty-fourths "
      "short by a rounding, is the second step all the same",
      sfield(L[5], "col") == "-1" and "send" not in L[5] and sfield(L[8], "col") == "0" and sfield(L[23], "col") == "0"
      and sfield(L[25], "beat") == "0.24999999999999997" and sfield(L[26], "col") == "1",
      "%s %s %s %s" % (sfield(L[5], "col"), sfield(L[8], "col"), sfield(L[25], "beat"), sfield(L[26], "col")))
L = sout("offs-exact")
check("a crossing's note-off and the pluck's each go on the frame of their own millisecond, not the next",
      "send 128,60,0" in L[6] and sfield(L[6], "crossoffs") == "-" and "send 128,60,0" in L[10] and sfield(L[10], "pluckoffs") == "-",
      "%s | %s" % (L[6][:40], L[10][:40]))
L = sout("out-rate")
# Fifty plucks 20 ms apart in the first second, then ten more as the window frees.
ons = sum(l.count("send 144,") for l in L[:150])
offs = sum(l.count("send 128,") for l in L[:182])  # to the frame at 2000 ms, which ends the first burst's last notes
check("the out sends forty note-ons in a second and drops the rest, counting them, then sends again as the second passes; every note-off goes",
      ons == 40 and int(sfield(L[149], "dropped")) == 10 and sum(l.count("send 144,") for l in L[:180]) == 50
      and offs == sum(l.count("send 144,") for l in L[:180]),
      "%d on, %s dropped, %d off" % (ons, sfield(L[149], "dropped"), offs))
L = sout("out-notes")
check("a note already sounding is ended before it is struck again, and a new channel lets the old one's notes go first",
      "send 133,64,0 :: send 149,64,127" in L[5] and "send 133,64,0 :: send 181,123,0" in L[7] and "send 150,64,1" in L[8],
      "%s | %s | %s" % (L[5][:70], L[7][:70], L[8][:70]))
L = sout("crossings")
check("a crossing's count gone up is its line's note, ended a tenth of a second on; a count gone down, or the lines off, is none",
      "send 144,60,102" in L[4] and "send 144,60,102" in L[7] and "send 144,67,102" in L[7] and "send 128,60,0" in L[9]
      and "send 144" not in L[13] and "send 144" not in L[16] and "send 144" not in L[18], " / ".join(l[:50] for l in L[4:19:3]))
# The count is not watched while the lines are off, so what it gained meanwhile is heard when they come on.
check("and a count that rose while the lines were off is heard when they come back on, at their new notes",
      "send 144,72,102" in L[21] and "send 144,74,102" in L[21], L[21][:90])
def snull(what, name, old, new):
    text = dict(sruns)[name]
    assert text.count(old) >= 1, old
    js, _ = sboth(text.replace(old, new, 1))
    _, cpp = sboth(text)
    check("and against " + what, kdiff(js, cpp) is not None)
snull("a cell a row lower, over the line between two pitches", "score-rows", "cell 31 2 0.7", "cell 32 2 0.7")
snull("the next key", "score-rows", "key 2 major", "key 3 major")
snull("a pluck a millisecond later", "out-rate", "at 400\npluck", "at 401\npluck")
snull("another channel", "out-notes", "port 1 6", "port 1 7")
check("and the comparison fails against the page's lines one command out of step",
      kdiff("\n".join(sjs.split("\n")[1:]), "\n".join(scpp.split("\n")[:-1])) is not None)

print("\n--- restore ---")
# The page's own `restore`, in a browser (restore_page.py), against
# scope::restoreSetup: every preset the page ships and random setups, each
# loaded in turn as the page loads them, and what each leaves in the
# instrument compared field by field - both layers' tones, the keyboard, the
# LFOs, the routings, the key, the crossings, the macros, the morph, the plane
# and the echo. A number to 1e-12: a cutoff is `Math.pow` against `std::pow`.
rexe = build("restore_cpp")
RTOOL = os.path.join(HERE, "tools", "restore_page.py")
# This half needs a browser: the page's `restore` writes into its controls.
# Without Playwright it says so and fails, rather than passing by not running.
try:
    import playwright  # noqa: F401
except ImportError:
    check("a browser to run the page's restore in (Playwright and Chromium)", False, "not installed")
    print("\nFAILED: " + ", ".join(fails)); sys.exit(1)
def rpage(*args): return subprocess.run([sys.executable, RTOOL] + list(args), check=True, capture_output=True, text=True).stdout
rsources = os.path.join(BUILD, "page_sources.json")
with open(rsources, "w") as f: f.write(rpage("--sources"))
def rdiff(a, b, path=""):
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b: out.append("%s.%s only in the %s" % (path, k, "page" if k in a else "port")); continue
            out += rdiff(a[k], b[k], path + "." + k)
        return out
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b): return ["%s: %d long against %d" % (path, len(a), len(b))]
        return [d for i, (x, y) in enumerate(zip(a, b)) for d in rdiff(x, y, "%s[%d]" % (path, i))]
    if isinstance(a, (bool, str)) or a is None or isinstance(b, (bool, str)) or b is None:
        return [] if a == b and type(a) == type(b) else ["%s: %r against %r" % (path, a, b)]
    return [] if abs(a - b) <= TOL * max(1.0, abs(a)) else ["%s: %r against %r" % (path, a, b)]
def rboth(setups, name):
    path = os.path.join(BUILD, name)
    with open(path, "w", encoding="utf-8") as f: f.write("\n".join(setups) + "\n")
    page = rpage(path).strip().split("\n")
    port = subprocess.run([rexe, path, rsources], check=True, capture_output=True, text=True).stdout.strip().split("\n")
    return page, port
def rbad(page, port):
    if len(page) != len(port): return ["%d against %d" % (len(page), len(port))]
    out = []
    for i, (x, y) in enumerate(zip(page, port)):
        d = rdiff(_json.loads(x), _json.loads(y))
        if d: out.append("setup %d: %s" % (i, "; ".join(d[:3])))
    return out

# The panel's table, held to the page's DOM control for control: a slider's
# range, step and starting value (a blank attribute is the browser's default),
# and a menu's options and the one it starts on.
pctl = _json.loads(rpage("--controls"))
cctl = _json.loads(subprocess.run([rexe, "--controls"], check=True, capture_output=True, text=True).stdout)
def dom(v, d): return float(v) if v != "" else d
ctl_bad = [k for k in set(pctl["ranges"]) | set(cctl["ranges"]) if k not in pctl["ranges"] or k not in cctl["ranges"]
           or [dom(pctl["ranges"][k][f], d) for f, d in (("min", 0), ("max", 100), ("step", 1), ("value", float("nan")))]
              != [cctl["ranges"][k][f] for f in ("min", "max", "step", "value")]]
ctl_bad += [k for k in set(pctl["selects"]) | set(cctl["selects"]) if pctl["selects"].get(k) != cctl["selects"].get(k)]
check("the panel's %d sliders and %d menus are the page's, range, step, options and all"
      % (len(pctl["ranges"]), len(pctl["selects"])), not ctl_bad and len(pctl["ranges"]) > 80, ", ".join(ctl_bad[:5]))
check("the %d sliders the morph walks are the page's, in the page's order" % len(pctl["morph"]),
      pctl["morph"] == cctl["morph"] and len(pctl["morph"]) > 70)
check("and that order is not the layout's", pctl["morph"] != [k for k in pctl["ranges"] if k in pctl["morph"]])
plib = rpage("--library").strip()
clib = subprocess.run([rexe, "--library"], check=True, capture_output=True, text=True).stdout.strip()
check("the preset library is the page's, preset for preset, character for character", plib == clib and len(plib) > 50000,
      "%d against %d characters" % (len(plib), len(clib)))
presets = rpage("--presets").strip().split("\n")
ppage, pport = rboth(presets, "restore_presets.txt")
pbad = rbad(ppage, pport)
check("all %d of the page's presets load to the same instrument" % len(presets), len(presets) > 250 and not pbad,
      pbad[0] if pbad else "")

rrng = random.Random(98)
SLIDERS = ["freq", "amp", "phase", "detail", "figureRate", "swingRate", "decay", "swingDrive", "inputDepth", "detune",
           "atk", "dec", "sus", "rel", "glide", "spinX", "spinY", "spinZ", "spinRate", "depth", "morph", "width", "table",
           "ring", "gen2Rate", "oscFm", "oscRing", "oscSync", "oscSub", "oscSpread", "shpDrive", "shpFold", "vcfCut",
           "vcfRes", "vcfTrack", "vcfEnvAmt", "vcfAtk", "vcfDec", "vcfSus", "vcfRel", "bAmp", "bAtk", "bDec", "bSus", "bRel",
           "bMorph", "bWidth", "bTable", "bFm", "bRing", "bSync", "bSub", "bSpread", "bDrive", "bFold", "bVcfCut", "bVcfRes",
           "bVcfTrack", "bVcfEnv", "bVcfAtk", "bVcfDec", "bVcfSus", "bVcfRel", "mac1", "mac2", "mac3", "mac4", "morphPos",
           "crossX", "crossY", "crossNoteX", "crossNoteY", "crossDecay", "crossLevel", "scoreVoices", "scoreOctaves",
           "arpOctaves", "threshLevel", "pluckNote", "planeRadius", "planeTwist", "planeScaleX", "planeScaleY", "planeShear",
           "delayMix", "delayMs", "delayFeedback", "chorusMix", "chorusRate", "chorusDepth", "chorusTime", "chorusFeedback",
           "qGlide", "bpm", "l0r", "l1r", "l0a", "l1a", "photoU", "photoV", "midiDrawCount", "midiDrawCountB", "splitAt"]
def rnumber():
    return rrng.choice([rrng.randint(-200, 4500), rrng.uniform(-50, 300), rrng.randint(0, 200) + 0.5, -0.0, 0, 1e21, -3e-7,
                        "12", " 12", "1e2", "+5", ".5", "5.", "abc", "", None, True, False, [3], [], "Infinity", "0x10"])
MENUS = {
    "shape": ["harmonic", "sine", "square", "pulse", "triangle", "ramp", "drawbars", "morph", "noise", "pink", "brown",
              "stepped", "bogus", 5],
    "figure": ["Circle", "Square", "Polygon", "Star", "Rose", "Heart", "Spiral", "Butterfly", "Bogus"],
    "model": ["Cube", "Tetrahedron", "Torus", "Knot", "Sphere"],
    "interval": [0, 3, 7, 12, "7", 7.0, 13, -1, 2.5, None],
    "oscRatio": [1, 0.5, 1.5, 2, 7, "1.5", 1.4, None], "oscSubOct": [1, 2, 3, "2"], "oscSubShape": ["square", "sine", "saw"],
    "oscUnison": [1, 2, 3, 5, 7, 4, "5"], "shpBits": [0, 8, 4, 1, 5], "shpRate": [0, 11025, 500, 600], "vcfType": [0, 1, 4, 5, "2"],
    "shpOS": [2, 4, "4", 3], "inputMode": [0, 1, 2, 3, 4, "1", None], "inputFrom": ["live", "gen2", "bogus"],
    "gen2Figure": ["Circle", "Rose", "Text", "Drawn", "Bogus", 5],
    "midiMode": ["dyad", "mono", "poly", "bogus"], "midiDrawWhich": ["outer", "lowest", "highest", "recent", "x"],
    "midiDrawWhichB": ["outer", "lowest", "recent", None], "layers": ["off", "split", "layer", "both"],
    "layerPair": ["each", "against", "x"], "midiDrive": ["wave,harmonograph,figure", "wave", "", "figure,wireframe", "x", 5, "waveform,figures"],
    "midiPlay": ["", "harmonograph", "figure,wireframe", "wave", "harmonographs"], "cc": ["", "16:Lower drawbars;42:Fx", " 7 : Vol ;x:y;99:a:b", "64:Sus\nx"],
    "bars": ["887000000", "008740000", "12", 887000000, "8 8 7 0 0 0 0 0 9", None, "8870000001"], "bBars": ["800000008", "x", None],
    "bShape": ["sine", "square", 5, None], "bRatio": [2, "3", 9], "bSubShape": ["sine", 3], "bUnison": [3, "x"],
    "l0y": ["", "1/4", "1/8t", "4", "bogus"], "l1y": ["", "2", "1/16"], "l0d": ["none", "phase", "freq", "amp", "bogus"],
    "l1d": ["none", "tumble", "depth", "ratio"], "keyScale": ["chromatic", "major", "blues", "whole", "bogus", ["major"]],
    "keyRoot": [-3, 14, 2.5, "2", 7, -0.0, 11], "crossX": [-150, -50, 50, 150, "x"], "crossY": [-120, -30, 30, 120],
    "scoreStep": ["1/16", "1/8", "1/4", "1/2"], "scoreLow": [36, 48, 60, 50, "48"], "arpMode": ["off", "up", "random", "x"],
    "arpRate": ["1/4", "1/16t", "1/2"], "threshWatch": ["env.live", "", "midi.key", 5], "delaySync": ["", "1/4", "1/8d", "x"],
    "planeMirror": [0, 1, 3, 4, "1"], "planeLimit": [0, 1, 2, 3], "planeOS": [1, 2, 4, 3], "planeKaleido": [0, 2, 8, 7],
    "planeSnap": [0, 6, 7], "macroNames": ["", "Wide|Bright||Fold", "a" * 20 + "|  b  |c|d|e", "|", 5],
    "morphA": ["", "=freq:330,amp:40", "=bogus:1,freq:x,amp:20:9", "=", "freq:1", 5, "=morphPos:50,freq:330",
               "=macro1:20,fileSeek:5,align:3,keysVelocity:9,freq:300"], "morphB": ["", "=freq:440", "=detail:9"],
    "mod": ["", "lfo1>gen.freq@0.400;photo.1>gen.amp@0.900", "macro.1>gen.morph@1.000;nope", None, 0, 5],
}
BOOLS = ["midiPolyJust", "midiHold", "midiTruth", "midiFollow", "photoOn", "quant", "crossOn", "scoreOn", "delayPingPong", "just"]
# The drawn cycles and the figures made of strokes, in and out of their
# grammars: a cycle of 256 bytes, of the wrong length, with white space atob
# forgives and with a character it does not, and one that is a default slot
# written out a byte at a time (which reads as the default within a byte's
# step, the encoder's own question); words that upper-case into more letters
# or fewer, and past twenty-four; SVG paths of every command, numbers run
# together, arcs' flags, junk, and a number after a Z; drawings with junk in
# their pairs and strange white space.
def rdefault_bytes(k):
    out = []
    peak = max(abs(math.sin(2 * math.pi * i / 4096) + 0.5 * math.sin(4 * math.pi * i / 4096) + 0.33 * math.sin(6 * math.pi * i / 4096)) for i in range(4096))
    for i in range(256):
        t = i / 256; th = 2 * math.pi * t
        v = (0.95 * (math.sin(th) + 0.5 * math.sin(2 * th) + 0.33 * math.sin(3 * th)) / peak if k == 1
             else 0.95 * (2 * t if t < 0.5 else 2 * t - 2) if k == 2 else (0.95 if t < 0.25 else -0.95 / 3) if k == 3 else math.sin(th))
        out.append((int(math.floor(v * 127 + 0.5)) + 256) % 256)
    return bytes(out)
def rcycle():
    c = rrng.random()
    if c < 0.4: return base64.b64encode(bytes(rrng.randrange(256) for _ in range(256))).decode()
    if c < 0.55: return base64.b64encode(rdefault_bytes(rrng.randrange(4))).decode()
    if c < 0.65: return base64.b64encode(bytes(rrng.randrange(256) for _ in range(rrng.choice([255, 257, 128])))).decode()
    if c < 0.75:
        t = base64.b64encode(bytes(rrng.randrange(256) for _ in range(256))).decode()
        k = rrng.randrange(len(t))
        return t[:k] + rrng.choice([" ", "\n", "\t", "!", "é", "="]) + t[k:]
    return rrng.choice(["", "abc", 5, None, "====", [1]])
def rcycles():
    parts = [rrng.choice(["", rcycle() if rrng.random() < 0.5 else ""]) for _ in range(rrng.choice([1, 2, 3, 3, 3, 4]))]
    parts = [p if isinstance(p, str) else "" for p in parts]
    return rrng.choice([",".join(parts), ",".join(parts), 5, None])
def rtext():
    c = rrng.random()
    if c < 0.5:
        return rrng.choice(["HELLO", "Scope 2", "straße", "ﬁne ﬂy", "ǰet", "ΐᾀ", "ﬓx", "a" * 30,
                            "line\nbreak\r!", "\U0001F600ok", "\ud800x", "", "lower case", "?!.,-+':/=", "ö" * 5,
                            "ıſ", "x" * 23 + "\U0001F600", 7, None])
    return "".join(rrng.choice("ABCXYZabcxyz0189 .,!?-+':/=#ßéﬀ") for _ in range(rrng.randint(0, 30)))
SVG_ARITY = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "T": 2, "A": 7, "Z": 0}
def rsvg():
    def num():
        v = rrng.choice([rrng.randint(-50, 50), round(rrng.uniform(-100, 100), rrng.randint(0, 4)), 0, 0.5, -0.5, 1000, 0.0015])
        t = repr(v)
        if rrng.random() < 0.1: t = t.replace("0.", ".", 1)
        if rrng.random() < 0.05: t += "e" + str(rrng.randint(-2, 2))
        if rrng.random() < 0.08 and not t.startswith("-"): t = "+" + t
        return t
    out = []
    for k in range(rrng.randint(1, 12)):
        c = "M" if k == 0 and rrng.random() < 0.9 else rrng.choice("MLHVCSQTAZmlhvcsqtaz")
        args = []
        for _ in range(1 if SVG_ARITY[c.upper()] == 0 else rrng.choice([1, 1, 1, 2])):
            for j in range(SVG_ARITY[c.upper()]):
                args.append((rrng.choice("01") if rrng.random() < 0.97 else "2") if c.upper() == "A" and j in (3, 4) else num())
        body = ("" if rrng.random() < 0.1 else rrng.choice([" ", ",", ", "])).join(args)
        out.append(c + rrng.choice(["", " "]) + body)
    d = rrng.choice([" ", "", "\n", "\t"]).join(out)
    r = rrng.random()
    if r < 0.08:
        k = rrng.randrange(len(d) + 1)
        d = d[:k] + rrng.choice("#x;! éB") + d[k:]
    elif r < 0.12: d += rrng.choice([" Z 5", "Z.5", " z -1"])
    elif r < 0.15: d = rrng.choice(["", "   ", "1 2", "M", "M0 0", "M0 0 L0 0", "M1e999 0 L1 1", 5, None])
    return d
def rdrawn():
    if rrng.random() < 0.15:
        return rrng.choice(["", "1,1", "a,b 1,1", ",5 1,1", "1,2,3 4,5", "Infinity,0 1,1", "0x10,1 1,1", ";;", 5, None])
    strokes = []
    for _ in range(rrng.randint(1, 4)):
        pts = ["%s,%s" % (round(rrng.uniform(-3, 3), rrng.randint(0, 4)), round(rrng.uniform(-3, 3), 4)) for _ in range(rrng.randint(1, 6))]
        strokes.append(rrng.choice([" ", "  ", "\t", " ", "　"]).join(pts))
    return rrng.choice([";", " ; ", ";;"]).join(strokes)
def rsetup():
    st = {}
    for key, make in (("cycle", rcycle), ("cycles", rcycles), ("figText", rtext), ("figPath", rsvg), ("figDrawn", rdrawn)):
        if rrng.random() < 0.15: st[key] = make()
    if rrng.random() < 0.1: st["figure"] = rrng.choice(["Text", "Path", "Drawn"])
    for _ in range(rrng.randint(1, 25)):
        r = rrng.random()
        if r < 0.5: st[rrng.choice(SLIDERS)] = rnumber()
        elif r < 0.85:
            k = rrng.choice(list(MENUS)); st[k] = rrng.choice(MENUS[k])
        elif r < 0.95:
            k = rrng.choice(BOOLS)
            st[k] = rrng.choice([True, False, 1, 0, "yes", "", None]) if k == "just" else rrng.choice([True, False, 1, "true", None])
        else: st["gen"] = rrng.choice(["wave", "harmonograph", "figure", "wireframe"])
    if rrng.random() < 0.3: st.pop("mod", None)
    return _json.dumps(st)
# The first two are the slider's own rules, made to be read: a half goes up,
# and a value that is not a number takes the slider's middle (detail runs from
# two to twelve, so seven).
# And two more made to be read: B's morph end is written against A's, which
# shows only when they differ on different sliders; and a routing list given
# as an array is read as its text, as String() reads it.
# And the cycles and figures, made to be read: a default slot written out a
# byte at a time, which is written back as no cycle at all; a word with an "ß", which
# upper-cases to two letters, beside the same word in capitals; a path read,
# then one with a number after its Z, refused, with the first kept; a path
# of more than six thousand points; one that starts with a number; a
# drawing whose points all coincide, which has no length to go round; the
# saw's slot a byte low at its second point, 0.94 of a step from the saw
# rather than within the half a step that reads as the default; a path of
# nothing but spaces, which is no path rather than a path of nothing; and a
# drawing of 3,200 points, which keeps the first three thousand.
FIG_MADE = [_json.dumps({"cycle": base64.b64encode(rdefault_bytes(0)).decode(), "cycles": ""}),
            _json.dumps({"figText": "stra\u00dfe", "figure": "Text"}), _json.dumps({"figText": "STRASSE", "figure": "Text"}),
            _json.dumps({"figPath": "M0 0 L10 0 L10 10", "figure": "Path"}),
            _json.dumps({"figPath": "M0 0 L10 0 L10 10 Z 5", "figure": "Path"}),
            _json.dumps({"figPath": "M0 0 " + "L1 1 L0 0 " * 3100}), _json.dumps({"figPath": "1 2 L 3 4"}),
            _json.dumps({"figDrawn": "0.5,0.5 0.5,0.5", "figure": "Drawn"}),
            _json.dumps({"cycles": "," + base64.b64encode(bytes(b - (i == 1) for i, b in enumerate(rdefault_bytes(2)))).decode() + ","}),
            _json.dumps({"figPath": "   "}),
            _json.dumps({"figDrawn": " ".join("%g,0" % (i / 1000) for i in range(1600)) + ";"
                                     + " ".join("0,%g" % (i / 1000) for i in range(1600)), "figure": "Drawn"})]
# And every character whose upper case is an ASCII letter or more than one
# character, as V8 has them, each between two letters - since a word of
# nothing the font draws compiles to no path at all, and then how many
# characters the upper case made cannot show.
FIG_UPPER_CPS = _json.loads(subprocess.run(["node", "-e", """
  const out = [];
  for (let c = 0x80; c <= 0x10FFFF; c++) {
    if (c >= 0xD800 && c <= 0xDFFF) continue;
    const up = Array.from(String.fromCodePoint(c).toUpperCase());
    if (up.length !== 1 || up.some((x) => x.codePointAt(0) < 0x80)) out.push(c);
  }
  console.log(JSON.stringify(out));"""], check=True, capture_output=True, text=True).stdout)
FIG_UPPER = [_json.dumps({"figText": "A" + chr(c) + "Z"}) for c in FIG_UPPER_CPS]
rsetups = ['{"freq":2014.5,"detail":"abc"}', '{"freq":"2014.5e0","detail":" 9"}',
           '{"morphA":"=freq:330","morphB":"=detail:9"}', '{"mod":["lfo1>gen.freq@0.500"]}'] + FIG_MADE + FIG_UPPER + [rsetup() for _ in range(400)] + [_json.dumps(_json.loads(rrng.choice(presets)) | _json.loads(rsetup())) for _ in range(100)]
rpg, rpt = rboth(rsetups, "restore_random.txt")
rb = rbad(rpg, rpt)
check("%d random setups, in and out of range, of every type, load to the same instrument" % len(rsetups), not rb, rb[0] if rb else "")
allr = [_json.loads(l) for l in ppage + rpg]
check("the setups reach every kind, both layers, the old LFO enum, the morph, the controllers and the tempo",
      {r["a"]["mode"] for r in allr} >= {"wave", "harmonograph", "figure", "wireframe"}
      and any(r["midi"]["layers"]["mode"] == "split" for r in allr) and any(r["a"]["amp"] != r["b"]["amp"] for r in allr)
      and any("lfo1>gen.phase" in r["mod"] for r in allr) and any(r["morph"]["a"] for r in allr)
      and any(r["midi"]["cc"] for r in allr) and any(r["lfos"][0]["rate"] != r["lfos"][0]["free"] for r in allr)
      and any(r["a"]["qMask"] not in (0, 4095) for r in allr) and any(r["echo"]["sync"] for r in allr))
fm = [_json.loads(l) for l in rpg[4:4 + len(FIG_MADE)]]
fu = [_json.loads(l) for l in rpg[4 + len(FIG_MADE):4 + len(FIG_MADE) + len(FIG_UPPER)]]
check("the %d characters whose upper case is an ASCII letter or longer each lay out as the page lays them out, and change the width"
      % len(FIG_UPPER), len(FIG_UPPER) == 104 and all(u["figure"]["textPath"] for u in fu)
      and len({_json.dumps(u["figure"]["textPath"]) for u in fu}) > 10)
check("a default slot written out a byte at a time is written back as no cycle, though what plays is the bytes",
      fm[0]["cycles"]["codes"] == ["", ""] and fm[0]["cycles"]["cycle"] != _json.loads(ppage[0])["cycles"]["cycle"]
      and fm[0]["cycles"]["points"][0] != _json.loads(ppage[0])["cycles"]["points"][0], repr(fm[0]["cycles"]["codes"]))
check("\"stra\u00dfe\" is written as STRASSE, seven letters, the \u00df upper-cased to two",
      fm[1]["figure"]["textPath"] == fm[2]["figure"]["textPath"] and fm[1]["figure"]["text"] != fm[2]["figure"]["text"]
      and fm[1]["figure"]["sent"] == fm[1]["figure"]["textPath"] and len(fm[1]["figure"]["textPath"]["xy"]) > 50)
check("a number after a Z is refused, and the path before it kept and still drawn",
      fm[4]["figure"]["fault"].startswith("That path could not be read: unexpected character")
      and fm[4]["figure"]["kept"] == "M0 0 L10 0 L10 10" and fm[4]["figure"]["sent"] == fm[3]["figure"]["sent"] != None,
      fm[4]["figure"]["fault"])
check("a drawing with no length draws nothing, and one past three thousand points keeps three thousand",
      fm[7]["figure"]["drawnPath"] is None and fm[7]["figure"]["drawn"] == "0.5,0.5 0.5,0.5"
      and len(fm[10]["figure"]["drawnPath"]["xy"]) == 2 * 3001 and fm[10]["figure"]["drawn"].replace(";", " ").count(" ") + 1 == 3000,
      "%r, %d" % (fm[7]["figure"]["drawnPath"], len(fm[10]["figure"]["drawnPath"]["xy"]) if fm[10]["figure"]["drawnPath"] else -1))
check("a slot 0.94 of a step from its default at one point is written back, and a path of spaces is no path and no complaint",
      fm[8]["cycles"]["codes"][1].startswith(",") and len(fm[8]["cycles"]["codes"][1]) > 300
      and fm[9]["figure"]["fault"] == "" and fm[9]["figure"]["kept"] == "" and fm[9]["figure"]["path"] is None,
      "%r %r" % (fm[8]["cycles"]["codes"][1][:12], fm[9]["figure"]["fault"]))
check("a path of more than six thousand points is refused as too detailed",
      fm[5]["figure"]["fault"] == "That path could not be read: too detailed: 6201 points, and the most is 6000.", fm[5]["figure"]["fault"])
rall = [_json.loads(l) for l in rpg]
faults = {(r["figure"]["fault"].split(" at ")[0].split(": ")[1] if ": " in r["figure"]["fault"] else r["figure"]["fault"]).rstrip(".")
          for r in rall}
check("the random setups reach every refusal, paths, drawings and cycles read and refused, and every figure of strokes sent",
      {"expected a number", "expected an arc flag", "unexpected character", "a path starts with a command",
       "Nothing in that path to draw"} <= faults
      and sum(1 for r in rall if r["cycles"]["codes"][0]) > 20 and sum(1 for r in rall if r["cycles"]["codes"][1]) > 5
      and sum(1 for r in rall if r["figure"]["drawnPath"]) > 20
      and {r["figure"]["sent"] is not None and (r["figure"]["sent"] == r["figure"]["textPath"], r["figure"]["sent"] == r["figure"]["path"],
           r["figure"]["sent"] == r["figure"]["drawnPath"]) for r in rall} >= {(True, False, False), (False, True, False), (False, False, True)},
      ", ".join(sorted(faults)))
r0, r1 = _json.loads(rpg[0]), _json.loads(rpg[1])
check("a slider snaps what it is given: a half goes up, and what is not a number takes its middle",
      r0["a"]["freq"] == 2015 and r0["a"]["detail"] == 7 and r1["a"]["freq"] == 2015 and r1["a"]["detail"] == 7,
      "%r %r, %r %r" % (r0["a"]["freq"], r0["a"]["detail"], r1["a"]["freq"], r1["a"]["detail"]))
# Nulls: the page told something different, and the port must disagree.
def rnull(what, index, change):
    setups = list(presets[:index + 1])
    setups[index] = _json.dumps(change(_json.loads(setups[index])))
    page, _ = rboth(setups, "restore_null.txt")
    check("and against " + what, rdiff(_json.loads(page[index]), _json.loads(pport[index])) != [])
rnull("a preset a hertz higher", 3, lambda st: st | {"freq": (st.get("freq", 220)) + 1})
rnull("a preset with layer B a step louder", 5, lambda st: st | {"bAmp": 21})
rnull("a preset on the next scale", 7, lambda st: st | {"keyScale": "dorian", "quant": True})
pdrawn = next(i for i, p in enumerate(presets) if '"cycle"' in p)
rnull("the drawn cycle's preset with one character of its cycle changed", pdrawn,
      lambda st: st | {"cycle": ("K" if st["cycle"][0] != "K" else "L") + st["cycle"][1:]})
ptext = next(i for i, p in enumerate(presets) if '"figText"' in p)
rnull("the written preset with one letter changed", ptext, lambda st: st | {"figText": "HELLP"})
ppath = next(i for i, p in enumerate(presets) if '"figPath"' in p)
rnull("the imported preset with one number of its path changed", ppath, lambda st: st | {"figPath": st["figPath"].replace("80", "81", 1)})
pdraw = next(i for i, p in enumerate(presets) if '"figDrawn"' in p)
rnull("the drawn preset with one point moved", pdraw, lambda st: st | {"figDrawn": st["figDrawn"].replace("0.6", "0.61", 1)})
check("and the comparison fails against the page's setups one out of step", rbad(ppage[1:], pport[:-1]) != [])

print("\n--- macros and the morph ---")
# A hand on the sliders, the morph's ends stored and the fader moved - by hand
# and by the matrix - and the macros' knobs, through the page's own handlers
# against scope::moveSlider, morphStore, morphStep and setMacro. Each line is
# an operation rather than a setup, and both runners put a frame (the matrix
# letting go of the fader, then the morph's step) before every line, since the
# page's own frames run between one batch of lines and the next.
ctl_ids = list(pctl["ranges"])
def mvalue(id):
    r = pctl["ranges"][id]; lo, hi = float(r["min"]), float(r["max"])
    c = rrng.random()
    if c < 0.75: return round(rrng.uniform(lo, hi), rrng.choice([0, 1, 2]))
    if c < 0.85: return rrng.choice([lo - 10, hi + 10, lo, hi])
    return rrng.choice(["abc", "1e2", " 5", "", "+3", "-0", "Infinity", "7.5"])
def mslider(pool): id = rrng.choice(pool); return {"op": "slider", "id": id, "value": mvalue(id)}
def mrun():
    out = [_json.loads(rrng.choice(presets)) if rrng.random() < 0.7 else {}]
    out += [mslider(ctl_ids) for _ in range(rrng.randint(2, 6))] + [{"op": "store", "end": "a"}]
    out += [mslider(ctl_ids + ["freq", "freq", "amp", "morph", "bar3", "delayMix", "planeTwist"]) for _ in range(rrng.randint(1, 8))]
    out.append({"op": "store", "end": "b"})
    for _ in range(rrng.randint(3, 10)):
        c = rrng.random()
        if c < 0.45: out.append({"op": "pos", "value": rrng.choice([0, 25, 50, 50.5, 75, 100, rrng.randint(0, 100)])})
        elif c < 0.6: out.append({"op": "mod", "value": rrng.choice([0, 0.1, -0.3, 0.5, 1.2, 0.00005, rrng.uniform(-1, 1)])})
        elif c < 0.65: out.append({"op": "hold", "value": rrng.choice([0, 0, -0.2, 0.3, rrng.uniform(-1, 1)])})
        elif c < 0.8: out.append({"op": "macro", "i": rrng.randint(0, 3), "value": rrng.choice([0, 33, 100, 150, -4, "x", rrng.randint(0, 100)])})
        elif c < 0.9: out.append({"op": "step"})
        else: out.append(mslider(ctl_ids))
    return out
# Made to be read, first: amp from 20 to 80 and frequency from 220 to 880, the
# fader a quarter and then half way; a push from the matrix below the step's
# threshold, then a real one; a hand on a slider with the fader at rest; the
# macros by their knobs and by their sliders, past the end; two sliders A
# holds that the page found in a different order from the one it lays out;
# the rates of a synced LFO and a synced delay moved; A stored with the fader
# half way; B stored while the matrix holds the fader a quarter back; and a
# push of a twentieth of a per cent, which only a slider two thousand steps
# wide can show.
MADE = [{}, {"op": "slider", "id": "amp", "value": 20}, {"op": "slider", "id": "freq", "value": 220},
        {"op": "store", "end": "a"},                                                             # 3
        {"op": "slider", "id": "amp", "value": 80}, {"op": "slider", "id": "freq", "value": 880},
        {"op": "store", "end": "b"},                                                             # 6
        {"op": "pos", "value": 25}, {"op": "pos", "value": 50},                                  # 7, 8
        {"op": "mod", "value": 0.00005}, {"op": "mod", "value": 0.25},                           # 9, 10
        {"op": "slider", "id": "amp", "value": 70}, {"op": "step"},                              # 11, 12
        {"op": "macro", "i": 1, "value": 33}, {"op": "slider", "id": "macro3", "value": 150},    # 13, 14
        {}, {"op": "slider", "id": "timebase", "value": 4}, {"op": "slider", "id": "freq", "value": 300},
        {"op": "store", "end": "a"},                                                             # 18
        {"l0y": "1/4"}, {"op": "slider", "id": "lfoRate0", "value": 50},                          # 19, 20
        {"delaySync": "1/4"}, {"op": "slider", "id": "delayMs", "value": 300},                    # 21, 22
        {}, {"op": "slider", "id": "amp", "value": 20}, {"op": "store", "end": "b"},
        {"op": "slider", "id": "amp", "value": 80}, {"op": "pos", "value": 50},                  # 26, 27
        {"op": "store", "end": "a"},                                                             # 28
        {"op": "hold", "value": -0.25}, {"op": "slider", "id": "amp", "value": 40},
        {"op": "store", "end": "b"}, {"op": "step"}, {"op": "hold", "value": 0},                 # 31, 32
        {}, {"op": "slider", "id": "level", "value": -1000}, {"op": "store", "end": "a"},
        {"op": "slider", "id": "level", "value": 1000}, {"op": "store", "end": "b"},
        {"op": "pos", "value": 50}, {"op": "mod", "value": 0.0005}]                              # 39, 40
mlines = [_json.dumps(o) for o in MADE] + [_json.dumps(o) for _ in range(90) for o in mrun()]
mpg, mpt = rboth(mlines, "morph_ops.txt")
mb = rbad(mpg, mpt)
check("%d operations on the sliders, the morph and the macros leave the same instrument" % len(mlines),
      not mb and len(mlines) > 1500, mb[0] if mb else "")
mp = [_json.loads(l) for l in mpg]
check("storing an end moves nothing and puts the fader at it",
      mp[6]["ranges"]["amp"] == 80 and mp[6]["morph"]["pos"] == 1 and mp[3]["morph"]["pos"] == 0
      and mp[6]["morph"]["b"] == "=freq:880,amp:80",
      "%r %r %r" % (mp[6]["ranges"]["amp"], mp[6]["morph"]["pos"], mp[6]["morph"]["b"]))
check("the fader a quarter of the way puts amp a quarter of the way, and its handler tells the generator",
      mp[7]["ranges"]["amp"] == 35 and mp[7]["a"]["amp"] == 0.35, "%r %r" % (mp[7]["ranges"]["amp"], mp[7]["a"]["amp"]))
check("frequency is walked in ratio: half way from 220 to 880 is 440, and the keyboard's panel follows",
      mp[8]["ranges"]["freq"] == 440 and mp[8]["a"]["freq"] == 440 and mp[8]["panel"]["freq"] == "440",
      "%r %r %r" % (mp[8]["ranges"]["freq"], mp[8]["a"]["freq"], mp[8]["panel"]["freq"]))
check("a push below the step's threshold moves nothing, and a quarter more from the matrix moves amp to 65",
      mp[9]["ranges"]["amp"] == 50 and mp[10]["ranges"]["amp"] == 65,
      "%r %r" % (mp[9]["ranges"]["amp"], mp[10]["ranges"]["amp"]))
check("a push of five ten-thousandths is past the step's threshold, and moves a wide slider a step",
      mp[39]["ranges"]["level"] == 0 and mp[40]["ranges"]["level"] == 1,
      "%r %r" % (mp[39]["ranges"]["level"], mp[40]["ranges"]["level"]))
check("a hand on a slider with the fader at rest stays where the hand put it",
      mp[11]["ranges"]["amp"] == 70 and mp[12]["ranges"]["amp"] == 70 and mp[12]["a"]["amp"] == 0.7,
      "%r %r" % (mp[11]["ranges"]["amp"], mp[12]["ranges"]["amp"]))
check("a macro's knob sets it, and its slider past the end holds it at one",
      mp[13]["macros"][1]["value"] == 0.33 and mp[14]["macros"][2]["value"] == 1 and mp[14]["ranges"]["macro3"] == 100,
      "%r %r" % (mp[13]["macros"][1]["value"], mp[14]["macros"][2]["value"]))
check("an end is written in the order the page found its sliders, not the order it lays them out",
      mp[18]["morph"]["a"] == "=freq:300,timebase:4", mp[18]["morph"]["a"])
check("LFO 1's rate moved while it is synced is its free rate, and it runs on at the beat's",
      mp[20]["lfos"][0]["free"] == 0.5 and mp[20]["lfos"][0]["rate"] == 2, repr(mp[20]["lfos"][0]))
check("the delay's time moved while it is synced is kept, and its slider goes on showing the beat's 500 ms",
      mp[22]["echo"]["ms"] == 300 and mp[22]["ranges"]["delayMs"] == 500,
      "%r %r" % (mp[22]["echo"]["ms"], mp[22]["ranges"]["delayMs"]))
check("storing A with the fader half way puts the fader at A",
      mp[27]["morph"]["pos"] == 0.5 and mp[28]["morph"]["pos"] == 0 and mp[28]["ranges"]["morphPos"] == 0)
check("B stored under the matrix's push moves nothing until the push changes",
      mp[31]["morph"]["pos"] == 1 and mp[32]["ranges"]["amp"] == 40, repr(mp[32]["ranges"]["amp"]))
# Counted without the fader's own slider, which a hand on the fader moves
# whether or not the morph does anything with it - with it in, a morph that
# walked nothing passed this.
def walked(i): return {k: v for k, v in mp[i]["ranges"].items() if k != "morphPos"} != {k: v for k, v in mp[i - 1]["ranges"].items() if k != "morphPos"}
mwalks = [i for i in range(1, len(mp)) if walked(i) and _json.loads(mlines[i]).get("op") in ("pos", "mod", "step")]
check("the runs walk the sliders %d times, by the fader and by the matrix" % len(mwalks),
      len(mwalks) > 100 and any(_json.loads(mlines[i])["op"] == "mod" for i in mwalks))
# Nulls: the page told something different, and the port must disagree.
def mnull(what, index, change):
    lines = list(mlines[:index + 1])
    lines[index] = _json.dumps(change(_json.loads(lines[index])))
    page, _ = rboth(lines, "morph_null.txt")
    check("and against " + what, rdiff(_json.loads(page[index]), _json.loads(mpt[index])) != [])
mnull("the fader a point further", 7, lambda o: o | {"value": 26})
mnull("a push a point stronger", 10, lambda o: o | {"value": 0.26})
mnull("the other macro", 13, lambda o: o | {"i": 2})
mnull("the end stored without timebase", 16, lambda o: o | {"value": 7})
check("and the comparison fails against the page's operations one out of step", rbad(mpg[1:], mpt[:-1]) != [])

print("\n--- menus, switches and buttons ---")
# A hand on a menu, a switch, a text box or a button that reaches the sound,
# through the page's own "change" and "click" handlers against
# scope::controlChange and controlClick - what the page in the plugin sends
# for each, as it sends a slider. Between presets and sliders, as a hand has
# them, and with values a menu has not got.
CMENUS = ["genMode", "interval", "figure", "inputMode", "inputFrom", "gen2Figure", "model", "shape", "shpOS", "oscRatio",
          "oscSubOct", "oscSubShape", "oscUnison", "shpBits", "shpRate", "vcfType", "planeMirror", "planeLimit",
          "planeKaleido", "planeSnap", "delaySync", "crossNoteX", "crossNoteY", "keyRoot", "keyScale", "midiDrawCount",
          "midiDrawWhich", "midiLayers", "midiLayerPair", "arpMode", "arpRate", "arpOctaves", "pluckNote", "scoreStep",
          "scoreVoices", "scoreLow", "scoreOctaves", "lfoShape0", "lfoSync0"]
CMORE = {"lfoShape1": pctl["selects"]["lfoShape0"]["options"], "lfoSync1": pctl["selects"]["lfoSync0"]["options"],
         "threshWatch": ["lfo1", "lfo2", "env.live", "macro.1", "onset", "threshold", "nobody", ""]}
CSWITCHES = ["delayPingPong", "crossOn", "quantise", "midiPolyJust", "midiHold", "midiTruth", "midiFollow", "midiDrive",
             "midiPlay", "scoreOn"]
CTEXT = {"figPathD": ["M0 0 L10 0 L10 10", "M0 0 L20 5 L5 20 Z", "junk", ""],
         **{"macroName%d" % i: ["Wobble", "Wob|ble  ", "   ", "a name much longer than sixteen", ""] for i in range(1, 5)}}
CCLICKS = ["tuneJust", "tuneEqual", "midiDyad", "midiMono", "midiPoly", "planeOS1", "planeOS2", "planeOS4"]
def cop():
    c = rrng.random()
    if c < 0.5:
        id = rrng.choice(CMENUS)
        opts = pctl["selects"][id]["options"]
        # A value the menu has not got reads "", which the page's keyboard
        # keeps as it is and the core's, holding one of a few, cannot. No menu
        # sends one - the page sends the menu's value - so not for those.
        odd = rrng.random() >= 0.92 and id not in ("midiLayers", "midiLayerPair", "midiDrawWhich")
        return {"op": "change", "id": id, "value": rrng.choice(["nonsense", "", "7"]) if odd else rrng.choice(opts)}
    if c < 0.6: id = rrng.choice(list(CMORE)); return {"op": "change", "id": id, "value": rrng.choice(CMORE[id] + ["nonsense"])}
    if c < 0.75: return {"op": "change", "id": rrng.choice(CSWITCHES), "value": rrng.random() < 0.5}
    if c < 0.82: id = rrng.choice(list(CTEXT)); return {"op": "change", "id": id, "value": rrng.choice(CTEXT[id])}
    if c < 0.95: return {"op": "click", "id": rrng.choice(CCLICKS)}
    if c < 0.97: return {"op": "slider", "id": "lfoRate1", "value": mvalue("lfoRate0")}
    return mslider(ctl_ids)
def crun():
    return [_json.loads(rrng.choice(presets)) if rrng.random() < 0.7 else {}] + [cop() for _ in range(rrng.randint(4, 14))]
# Made to be read: each family once, with what it should leave. The figure's
# path is drawn while the Path figure is chosen; the LFO is locked to a
# quarter at 120 and let go; the threshold is set to watch an event, which it
# cannot.
CMADE = [{}, {"op": "change", "id": "genMode", "value": "harmonograph"},                                  # 1
         {"op": "change", "id": "genMode", "value": "figure"}, {"op": "change", "id": "figure", "value": "Path"},
         {"op": "change", "id": "figPathD", "value": "M0 0 L20 5 L5 20 Z"},                              # 4
         {"op": "change", "id": "genMode", "value": "wave"}, {"op": "change", "id": "shape", "value": "square"},
         {"op": "change", "id": "oscUnison", "value": "3"}, {"op": "change", "id": "vcfType", "value": "2"},  # 7, 8
         {"op": "change", "id": "shpOS", "value": "4"}, {"op": "change", "id": "planeKaleido", "value": "6"},  # 9, 10
         {"op": "click", "id": "planeOS4"}, {"op": "change", "id": "delaySync", "value": "1/4"},             # 11, 12
         {"op": "change", "id": "delayPingPong", "value": True}, {"op": "change", "id": "crossOn", "value": True},
         {"op": "change", "id": "crossNoteX", "value": "60"}, {"op": "change", "id": "keyScale", "value": "major"},
         {"op": "change", "id": "quantise", "value": True},                                                  # 17
         {"op": "change", "id": "midiLayers", "value": "split"}, {"op": "change", "id": "midiLayerPair", "value": "against"},
         {"op": "click", "id": "midiPoly"}, {"op": "click", "id": "tuneEqual"},                              # 20, 21
         {"op": "change", "id": "arpMode", "value": "up"}, {"op": "change", "id": "arpRate", "value": "1/16"},
         {"op": "change", "id": "arpOctaves", "value": "2"},                                                 # 24
         {"op": "change", "id": "lfoSync0", "value": "1/4"}, {"op": "change", "id": "lfoSync0", "value": ""},  # 25, 26
         {"op": "change", "id": "lfoShape1", "value": "square"},                                             # 27
         {"op": "change", "id": "threshWatch", "value": "lfo2"}, {"op": "change", "id": "threshWatch", "value": "onset"},
         {"op": "change", "id": "macroName2", "value": "Wob|ble  "}, {"op": "change", "id": "macroName3", "value": "   "},
         {"op": "change", "id": "scoreOn", "value": True}, {"op": "change", "id": "scoreVoices", "value": "4"},  # 32, 33
         {"op": "change", "id": "shape", "value": "nonsense"}, {"op": "click", "id": "tuneJust"},           # 34, 35
         {"op": "change", "id": "keyRoot", "value": "2"}, {"op": "change", "id": "keyScale", "value": "minor"},  # 36, 37
         {"op": "change", "id": "scoreVoices", "value": "nonsense"},                                       # 38
         {"op": "change", "id": "genMode", "value": "harmonograph"}, {"op": "change", "id": "midiPlay", "value": True},  # 39, 40
         {"op": "slider", "id": "lfoRate1", "value": 120}, {"op": "change", "id": "lfoSync1", "value": "1/4"},  # 41, 42
         {"op": "slider", "id": "lfoRate1", "value": 300}]                                                 # 43
clines = [_json.dumps(o) for o in CMADE] + [_json.dumps(o) for _ in range(150) for o in crun()]
cpg, cpt = rboth(clines, "control_ops.txt")
cb = rbad(cpg, cpt)
check("%d menus, switches, text boxes and buttons leave the same instrument" % len(clines),
      not cb and len(clines) > 1200, cb[0] if cb else "")
cp = [_json.loads(l) for l in cpg]
check("the kind menu changes the kind, and a path drawn under the Path figure is what the figure sends",
      cp[1]["a"]["mode"] == "harmonograph" and cp[3]["a"]["figure"] == "Path" and cp[4]["figure"]["sent"] is not None
      and cp[4]["figure"]["sent"] != cp[3]["figure"]["sent"], "%r %r" % (cp[1]["a"]["mode"], cp[3]["a"]["figure"]))
check("the shape, the unison, the filter's type and the oversampling reach the tone",
      cp[6]["a"]["shape"] == "square" and cp[7]["a"]["unison"] == 3 and cp[8]["a"]["vcfType"] == 2 and cp[9]["a"]["shapeOS"] == 4)
check("the kaleidoscope's menu and the plane's 4x button reach the tone",
      cp[10]["a"]["planeKaleido"] == 6 and cp[11]["plane"]["os"] == 4 and cp[11]["a"]["planeOS"] == 4)
check("the echo synced to a quarter at 120 is 500 ms, and ping-pong switched on",
      cp[12]["a"]["delayMs"] == 500 and cp[13]["a"]["delayPingPong"] is True, repr(cp[12]["a"]["delayMs"]))
check("the crossings switched on at middle C, and C major quantised is the mask 2741",
      cp[14]["a"]["crossOn"] is True and abs(cp[15]["a"]["crossHzX"] - 261.6255653005986) < 1e-9
      and cp[17]["a"]["qMask"] == 2741, repr(cp[17]["a"]["qMask"]))
check("the split, the pairing, poly and the tuning both ways reach the keyboard and the tone",
      cp[18]["midi"]["layers"]["mode"] == "split" and cp[19]["midi"]["layers"]["pair"] == "against"
      and cp[19]["midi"]["mode"] != "poly" and cp[20]["midi"]["mode"] == "poly"
      and cp[20]["a"]["just"] is True and cp[21]["a"]["just"] is False and cp[35]["a"]["just"] is True)
check("the arpeggiator's menus reach what it plays",
      cp[24]["arpPlays"] == {"mode": "up", "rate": "1/16", "octaves": 2}, repr(cp[24]["arpPlays"]))
check("LFO 1 locked to a quarter at 120 runs at 2 Hz from the beat, and let go goes back to its free rate",
      cp[25]["lfos"][0]["rate"] == 2 and cp[24]["lfos"][0]["phase"] == 1 and cp[25]["lfos"][0]["phase"] == 0 and cp[25]["lfos"][0]["epoch"] > cp[24]["lfos"][0]["epoch"]
      and cp[26]["lfos"][0]["rate"] == cp[24]["lfos"][0]["rate"] and cp[27]["lfos"][1]["shape"] == "square",
      repr(cp[25]["lfos"][0]))
check("the threshold watches another source, and an event is nothing it can watch",
      cp[28]["thresh"]["watch"] == "lfo2" and cp[29]["thresh"]["watch"] == "", repr(cp[29]["thresh"]))
check("a macro's name loses its bars and spaces, and a name of spaces is no name",
      cp[30]["macros"][1]["name"] == "Wobble" and cp[31]["macros"][2]["name"] == "Macro 3")
check("with the quantiser on, the key's root and its scale each move the mask at once",
      cp[35]["key"]["quantise"] is True and len({cp[35]["a"]["qMask"], cp[36]["a"]["qMask"], cp[37]["a"]["qMask"]}) == 3,
      "%r %r %r" % (cp[35]["a"]["qMask"], cp[36]["a"]["qMask"], cp[37]["a"]["qMask"]))
check("the score switched on with four voices, and a number of voices the menu has not got is one",
      cp[32]["score"]["on"] is True and cp[33]["score"]["voices"] == 4 and cp[38]["score"]["voices"] == 1)
check("LFO 2's rate moves it, and moved while it is synced is its free rate, the beat's going on",
      cp[41]["lfos"][1]["rate"] == 1.2 and cp[41]["lfos"][1]["free"] == 1.2 and cp[42]["lfos"][1]["rate"] == 2
      and cp[43]["lfos"][1]["free"] == 3 and cp[43]["lfos"][1]["rate"] == 2, repr([cp[i]["lfos"][1] for i in (41, 42, 43)]))
check("the harmonograph played at the note's pitch by its switch",
      cp[39]["midi"]["play"]["harmonograph"] is False and cp[40]["midi"]["play"]["harmonograph"] is True, repr(cp[40]["midi"]["play"]))
check("a shape the menu has not got is no shape", cp[34]["a"]["shape"] != "nonsense", repr(cp[34]["a"]["shape"]))
cops = [_json.loads(l) for l in clines]
cmoved = {o["id"] for i, o in enumerate(cops) if o.get("op") in ("change", "click") and i and rdiff(cp[i], cp[i - 1])}
call = set(CMENUS) | set(CMORE) | set(CSWITCHES) | set(CTEXT) | set(CCLICKS)
check("the runs move something with every one of the %d controls" % len(call), cmoved >= call, ", ".join(sorted(call - cmoved)))
def cnull(what, index, change):
    lines = list(clines[:index + 1])
    lines[index] = _json.dumps(change(_json.loads(lines[index])))
    page, _ = rboth(lines, "control_null.txt")
    check("and against " + what, rdiff(_json.loads(page[index]), _json.loads(cpt[index])) != [])
cnull("the other kind", 1, lambda o: o | {"value": "wireframe"})
cnull("the 2x button", 11, lambda o: o | {"id": "planeOS2"})
cnull("the LFO locked to an eighth", 25, lambda o: o | {"value": "1/8"})
cnull("the threshold watching LFO 1", 28, lambda o: o | {"value": "lfo1"})
cnull("another name", 30, lambda o: o | {"value": "Wibble"})
cnull("the switch the other way", 13, lambda o: o | {"value": False})
check("and the comparison fails against the page's operations one out of step", rbad(cpg[1:], cpt[:-1]) != [])

print("\n--- layer B on the panel ---")
# With the layers on, the A and B buttons choose which layer the panel's
# voice controls show and write: B shown keeps what A's controls said and
# writes B's tone into them, each through its law back. The page's own
# handlers against scope::showLayerOnPanel and the keyboard's editLayer,
# with a keyboard there - the layers are only on with one.
LSLIDERS = ["amp", "envAttack", "envDecay", "envSustain", "envRelease", "morph", "width", "table", "oscFm", "oscRing",
            "oscSync", "oscSub", "oscSpread", "shpDrive", "shpFold", "vcfCut", "vcfRes", "vcfTrack", "vcfEnvAmt",
            "vcfAtk", "vcfDec", "vcfSus", "vcfRel"] + ["bar%d" % k for k in range(9)]
LMENUS = ["shape", "oscRatio", "oscSubOct", "oscSubShape", "oscUnison", "shpBits", "shpRate", "vcfType"]
def lop():
    c = rrng.random()
    if c < 0.45: return mslider(LSLIDERS)
    if c < 0.65: id = rrng.choice(LMENUS); return {"op": "change", "id": id, "value": rrng.choice(pctl["selects"][id]["options"])}
    if c < 0.8: return {"op": "click", "id": rrng.choice(["midiEditA", "midiEditB", "midiEditB"])}
    if c < 0.86: return {"op": "change", "id": "midiLayers", "value": rrng.choice(["off", "split", "layer", "layer"])}
    if c < 0.9: return {"op": "click", "id": rrng.choice(["midiPoly", "midiPoly", "midiMono", "midiDyad"])}
    if c < 0.92: return {"op": "keys", "value": rrng.random() < 0.7}
    if c < 0.94: return {"op": "change", "id": "genMode", "value": rrng.choice(["wave", "wave", "figure"])}
    if c < 0.96: return {"op": "store", "end": rrng.choice(["a", "b"])}
    if c < 0.98: return {"op": "pos", "value": rrng.randint(0, 100)}
    return _json.loads(rrng.choice(presets))
def lrun():
    start = [_json.loads(rrng.choice(presets)) if rrng.random() < 0.6 else {}, {"op": "keys", "value": True},
             {"op": "change", "id": "genMode", "value": "wave"}, {"op": "click", "id": "midiPoly"},
             {"op": "change", "id": "midiLayers", "value": rrng.choice(["split", "layer"])}, {"op": "click", "id": "midiEditB"}]
    return start + [lop() for _ in range(rrng.randint(6, 16))]
# Made to be read: A's level set to 30, B chosen and its level set to 80,
# its shape, a drawbar and its unison; A chosen again; B chosen and the
# layers turned off under it; a preset loaded with B chosen; the keyboard gone.
LMADE = [{}, {"op": "keys", "value": True}, {"op": "click", "id": "midiPoly"},                    # 0-2
         {"op": "change", "id": "midiLayers", "value": "layer"}, {"op": "slider", "id": "amp", "value": 30},  # 3, 4
         {"op": "click", "id": "midiEditB"}, {"op": "slider", "id": "amp", "value": 80},            # 5, 6
         {"op": "change", "id": "shape", "value": "square"}, {"op": "slider", "id": "bar3", "value": 8},  # 7, 8
         {"op": "change", "id": "oscUnison", "value": "3"}, {"op": "click", "id": "midiEditA"},     # 9, 10
         {"op": "click", "id": "midiEditB"}, {"op": "change", "id": "midiLayers", "value": "off"},  # 11, 12
         {"op": "change", "id": "midiLayers", "value": "layer"}, _json.loads(presets[4]),           # 13, 14
         {"op": "keys", "value": False}]                                                           # 15
llines = [_json.dumps(o) for o in LMADE] + [_json.dumps(o) for _ in range(80) for o in lrun()]
lpg, lpt = rboth(llines, "layerb_ops.txt")
lb = rbad(lpg, lpt)
check("%d hands with the layers on, layer A and layer B on the panel in turn, leave the same instrument" % len(llines),
      not lb and len(llines) > 900, lb[0] if lb else "")
lp = [_json.loads(l) for l in lpg]
check("with the layers on, B chosen shows B on the panel and A's level stays A's",
      lp[4]["ranges"]["amp"] == 30 and lp[4]["panelLayer"] == 0 and lp[5]["panelLayer"] == 1
      and lp[5]["ranges"]["amp"] == round(lp[5]["b"]["amp"] * 100) and lp[5]["ranges"]["amp"] != 30,
      "%r %r" % (lp[5]["panelLayer"], lp[5]["ranges"]["amp"]))
check("a slider, a menu and a drawbar moved with B shown are B's, and A's are untouched",
      lp[6]["b"]["amp"] == 0.8 and lp[6]["a"]["amp"] == 0.3 and lp[7]["b"]["shape"] == "square"
      and lp[7]["a"]["shape"] != "square" and lp[8]["b"]["bars"][3] == 8 and lp[8]["a"]["bars"] != lp[8]["b"]["bars"]
      and lp[9]["b"]["unison"] == 3 and lp[9]["a"]["unison"] != 3,
      "%r %r" % (lp[7]["a"]["shape"], lp[9]["a"]["unison"]))
check("A chosen again puts A's controls back as they were, its menus among them",
      lp[10]["panelLayer"] == 0 and lp[10]["ranges"]["amp"] == 30 and lp[10]["menus"]["shape"] == lp[4]["menus"]["shape"]
      and lp[10]["menus"]["oscUnison"] == lp[4]["menus"]["oscUnison"], repr(lp[10]["menus"]))
check("the layers turned off under B put A back on the panel, and on again show B",
      lp[11]["panelLayer"] == 1 and lp[12]["panelLayer"] == 0 and lp[12]["ranges"]["amp"] == 30 and lp[13]["panelLayer"] == 1)
p4 = _json.loads(presets[4])
check("a preset loaded with B chosen is the preset's in A, and in B where it gives B nothing of its own",
      lp[14]["a"]["shape"] == p4["shape"] == lp[14]["b"]["shape"] and lp[14]["a"]["amp"] == 0.55 == lp[14]["b"]["amp"]
      and lp[14]["a"]["bars"] == [0, 0, 8, 7, 4, 0, 0, 0, 0] == lp[14]["b"]["bars"],
      "A %r %r %r, B %r %r %r" % (lp[14]["a"]["shape"], lp[14]["a"]["amp"], lp[14]["a"]["bars"], lp[14]["b"]["shape"],
                                  lp[14]["b"]["amp"], lp[14]["b"]["bars"]))
check("and the keyboard gone shows A", lp[15]["panelLayer"] == 0, repr(lp[15]["panelLayer"]))
lmoved = sum(1 for i in range(1, len(lp)) if lp[i]["panelLayer"] != lp[i - 1]["panelLayer"])
check("the runs move the panel between the layers %d times, and write B %d times" % (lmoved,
      sum(1 for i in range(1, len(lp)) if lp[i]["b"] != lp[i - 1]["b"] and lp[i - 1]["panelLayer"] == 1)),
      lmoved > 100 and sum(1 for i in range(1, len(lp)) if lp[i]["b"] != lp[i - 1]["b"] and lp[i - 1]["panelLayer"] == 1) > 150)
def lnull(what, index, change):
    lines = list(llines[:index + 1])
    lines[index] = _json.dumps(change(_json.loads(lines[index])))
    page, _ = rboth(lines, "layerb_null.txt")
    check("and against " + what, rdiff(_json.loads(page[index]), _json.loads(lpt[index])) != [])
lnull("A chosen where B was", 5, lambda o: o | {"id": "midiEditA"})
lnull("B's level a step lower", 6, lambda o: o | {"value": 79})
lnull("the layers split where they were layered", 13, lambda o: o | {"value": "split"})
check("and the comparison fails against the page's operations one out of step", rbad(lpg[1:], lpt[:-1]) != [])

print("\n--- the fade from the plugin ---")
# The fade the page keeps in its own storage, sent whole to the plugin when
# it is saved and handed back by the plugin's state: the page's own
# fadeFromHost against scope::fadeFromPage, with what the page sends and
# with what a code could hold - a mode it has not got, numbers as words, the
# names the fade had before its envelope, an envelope missing, nothing.
def fenv():
    keys = ["delay", "attack", "attackMid", "decay", "decayMid", "sustain", "release", "releaseMid", "restart", "loop",
            "seconds", "inSeconds", "outSeconds", "inMid", "outMid"]
    out = {}
    for k in rrng.sample(keys, rrng.randint(0, len(keys))):
        c = rrng.random()
        out[k] = (rrng.random() < 0.5 if k in ("restart", "loop") and c < 0.7 else
                  round(rrng.uniform(-1, 12), rrng.choice([0, 1, 2])) if c < 0.75 else
                  rrng.choice([None, "3", "x", True, [], 0]))
    return out
def fvalue():
    c = rrng.random()
    if c < 0.08: return None
    if c < 0.12: return rrng.choice(["both", 3, []])
    v = {}
    if rrng.random() < 0.95: v["mode"] = rrng.choice(["off", "in", "out", "both", "both", "sideways", None])
    # An envelope may be something other than an object: an array is one to
    # the page's typeof, with nothing in it; the rest are the default.
    odd = lambda: rrng.choice([[], [1, 2], 5, "x", None, True])
    if rrng.random() < 0.95: v["envs"] = [fenv() if rrng.random() < 0.85 else odd() for _ in range(rrng.choice([0, 1, 2, 2, 2, 3]))] if rrng.random() < 0.95 else "no"
    return v
FULL = {"delay": 0.25, "attack": 1.5, "attackMid": 0.7, "decay": 0.4, "decayMid": 0.3, "sustain": 0.6, "release": 3,
        "releaseMid": 0.2, "restart": True, "loop": False}
FMADE = [{}, {"op": "fade", "value": {"mode": "both", "envs": [FULL, dict(FULL, attack=0.5, loop=True)]}},      # 1
         {"op": "fade", "value": None},                                                                       # 2
         {"op": "fade", "value": {"mode": "in", "envs": [{"seconds": 4, "attack": None}, {"inSeconds": 0.3, "outMid": 0.8}]}},  # 3
         {"op": "fade", "value": {"mode": "sideways", "envs": [{"attack": 99, "sustain": "0.5", "delay": None}]}}]  # 4
flines = [_json.dumps(o) for o in FMADE] + [_json.dumps({"op": "fade", "value": fvalue()}) for _ in range(300)]
fpg, fpt = rboth(flines, "fade_ops.txt")
fb = rbad(fpg, fpt)
check("%d fades handed back by the plugin, as the page sends them and as a code could hold them, are the same fade" % len(flines),
      not fb, fb[0] if fb else "")
fp = [_json.loads(l)["fade"] for l in fpg]
check("the page's fade comes back whole, mode and both layers' envelopes",
      fp[1]["mode"] == "both" and fp[1]["envs"][0] == FULL and fp[1]["envs"][1]["attack"] == 0.5 and fp[1]["envs"][1]["loop"] is True,
      repr(fp[1]))
check("none is the fade's defaults, off with two-second fades",
      fp[2]["mode"] == "off" and fp[2]["envs"][0]["attack"] == 2 and fp[2]["envs"][1]["release"] == 2 and fp[2]["envs"][0]["restart"] is False,
      repr(fp[2]))
check("the names from before the envelope still read, a null attack beside seconds is the seconds",
      fp[3]["envs"][0]["attack"] == 4 and fp[3]["envs"][0]["release"] == 4 and fp[3]["envs"][1]["attack"] == 0.3
      and fp[3]["envs"][1]["releaseMid"] == 0.8, repr(fp[3]["envs"]))
check("a mode it has not got is off; a time is held to ten seconds, a word that is a number is that number, null is nought",
      fp[4]["mode"] == "off" and fp[4]["envs"][0]["attack"] == 10 and fp[4]["envs"][0]["sustain"] == 0.5 and fp[4]["envs"][0]["delay"] == 0
      and fp[4]["envs"][1] == fp[2]["envs"][1], repr(fp[4]["envs"][0]))
def fnull(what, index, change):
    lines = list(flines[:index + 1])
    lines[index] = _json.dumps(change(_json.loads(lines[index])))
    page, _ = rboth(lines, "fade_null.txt")
    check("and against " + what, rdiff(_json.loads(page[index]), _json.loads(fpt[index])) != [])
fnull("an attack a tenth longer", 1, lambda o: {"op": "fade", "value": {"mode": "both", "envs": [dict(FULL, attack=1.6), o["value"]["envs"][1]]}})
fnull("fading in only", 1, lambda o: {"op": "fade", "value": dict(o["value"], mode="in")})

print("\n--- the view ---")
# What the screen is set to draw - the capture's settings and the walk's - as
# the page's restore, its sliders and its menus, switches and buttons leave
# them, against the core's: what the plugin draws its own grid by, for the
# photocell and the picture's sources with the window closed. Every run above
# compares the view too; these are the view's own hands, between presets,
# with values a menu has not got and a reticle off the screen.
VSLIDERS = ["timebase", "level", "position", "holdoff", "ch1Scale", "ch1Offset", "ch2Scale", "ch2Offset", "acCorner", "lag",
            "rotate", "filterCutoff", "filterRes", "zoom"]
VMENUS = {"filterType": pctl["selects"]["filterType"]["options"], "beamLevel": pctl["selects"]["beamLevel"]["options"],
          "persistence": pctl["selects"]["persistence"]["options"], "xyX": ["0", "1"], "xyY": ["0", "1"]}
VSWITCHES = ["ch1On", "ch1Ac", "ch2On", "ch2Ac", "midSide", "lagOn", "filterOn", "beamXY", "beamYT"]
VCLICKS = ["dispYT", "dispXY", "dispSpect", "edgeRising", "edgeFalling", "modeAuto", "modeNormal", "modeSingle", "lagAuto",
           "lagManual", "seeDry", "seeWet", "measurePre", "measurePost", "layStack", "layOver", "trigSource0", "trigSource1",
           "photoButton", "clearButton"]
def vop():
    c = rrng.random()
    if c < 0.3: return mslider(VSLIDERS)
    if c < 0.5:
        id = rrng.choice(list(VMENUS))
        return {"op": "change", "id": id, "value": rrng.choice(VMENUS[id] + ["nonsense", "2"])}
    if c < 0.65: return {"op": "change", "id": rrng.choice(VSWITCHES), "value": rrng.random() < 0.5}
    if c < 0.88: return {"op": "click", "id": rrng.choice(VCLICKS)}
    # The kind menu, which turns the screen to X-Y for a drawing - from Y-T, and only from Y-T.
    if c < 0.9: return {"op": "change", "id": "genMode", "value": rrng.choice(["wave", "harmonograph", "figure"])}
    return {"op": "change", "id": "photoReticle",
            "value": rrng.choice(["%.3f,%.3f" % (rrng.random(), rrng.random()), "1.5,-0.2", "abc,0.5", "0.5,", "0.5"])}
# Setups that name lanes the generator has not got, or one lane twice: the
# trigger and the pair are held to the two lanes there are.
VODD = [{"trig": 3}, {"trig": -1}, {"trig": 1.5}, {"xy0": 3, "xy1": 3}, {"xy0": 1, "xy1": 1}, {"xy0": 0, "xy1": 0},
        {"xy0": 5, "xy1": 0}, {"xy0": -1, "xy1": 1}, {"display": "xy", "persistence": "0"}, {"timebase": 12},
        # And a corner off the slider's range and one off its step, which the slider holds to them.
        {"acHz": 5000}, {"acHz": 2.5}]
# And setups that move every field of the view, which the presets mostly leave
# at its default: the holdoff, the edge, the trigger's mode, a lane off.
def vsetup():
    pick, r = rrng.choice, rrng.random
    return {"timebase": rrng.randint(0, 8), "level": rrng.randint(-1000, 1000), "position": rrng.randint(0, 100),
            "holdoff": rrng.randint(0, 500), "edge": pick(["rising", "falling", "rising"]), "trig": rrng.randint(0, 1),
            "trigMode": pick(["auto", "normal", "single"]), "c0on": r() < 0.8, "c1on": r() < 0.8, "c0ac": r() < 0.3,
            "c1ac": r() < 0.3, "c0s": pick([0, -3, -6, -12, -24, -50, -1.5, -9, -45]), "c1s": pick([0, -6, -18, -20]),
            "c0o": pick([rrng.randint(-100, 100), round(rrng.uniform(-100, 100), 1)]), "c1o": rrng.randint(-100, 100), "midSide": r() < 0.3, "acHz": rrng.randint(5, 200), "lagOn": r() < 0.4,
            "lagMs": round(rrng.uniform(0, 40), 1), "lagAuto": r() < 0.5, "rotate": rrng.randint(-100, 100), "fOn": r() < 0.4,
            "fType": pick(VMENUS["filterType"]), "fCut": rrng.randint(0, 1000), "fRes": rrng.randint(0, 100),
            "fSee": pick(["pre", "post"]), "mSee": pick(["pre", "post"]), "xy0": rrng.randint(0, 1), "xy1": rrng.randint(0, 1),
            "beam": pick(VMENUS["beamLevel"]), "beamXY": r() < 0.7, "beamYT": r() < 0.4, "display": pick(["yt", "xy", "spect"]),
            "persistence": pick(VMENUS["persistence"]), "span": pick(["2", "5", "10", "30"]), "zoom": rrng.randint(0, 24)}
def vrun():
    c = rrng.random()
    first = _json.loads(rrng.choice(presets)) if c < 0.4 else vsetup() if c < 0.8 else rrng.choice(VODD) if c < 0.9 else {}
    return [first] + [vop() for _ in range(rrng.randint(4, 14))]
# Made to be read: each family once, with what it should leave.
VMADE = [{}, {"op": "click", "id": "dispXY"}, {"op": "change", "id": "persistence", "value": "0.3"},       # 1, 2
         {"op": "click", "id": "dispYT"}, {"op": "slider", "id": "zoom", "value": 8},                       # 3, 4
         {"op": "slider", "id": "ch1Scale", "value": 3}, {"op": "change", "id": "lagOn", "value": True},    # 5, 6
         {"op": "change", "id": "midSide", "value": True}, {"op": "change", "id": "xyX", "value": "1"},     # 7, 8
         {"op": "click", "id": "trigSource1"}, {"op": "change", "id": "photoReticle", "value": "0.25,0.6"},  # 9, 10
         {"op": "change", "id": "photoReticle", "value": "2,-1"}, {"op": "click", "id": "photoButton"},    # 11, 12
         {"op": "change", "id": "filterType", "value": "notch"}, {"op": "change", "id": "beamLevel", "value": "nonsense"},
         {"op": "click", "id": "seeDry"}, {"op": "slider", "id": "timebase", "value": 7}]                   # 15, 16
vlines = [_json.dumps(o) for o in VMADE + VODD] + [_json.dumps(o) for _ in range(120) for o in vrun()]
vpg, vpt = rboth(vlines, "view_ops.txt")
vb = rbad(vpg, vpt)
check("%d of the view's sliders, menus, switches, buttons and reticle moves leave the same view" % len(vlines),
      not vb and len(vlines) > 1000, vb[0] if vb else "")
vp = [_json.loads(l)["view"] for l in vpg]
vph = [_json.loads(l)["photo"] for l in vpg]
check("X-Y with no persistence is nudged to 0.12 on the way in, and a persistence chosen after it stays",
      vp[0]["persistence"] == 0 and vp[1]["display"] == "xy" and vp[1]["persistence"] == 0.12 and vp[2]["persistence"] == 0.3
      and vp[3]["display"] == "yt", "%r %r %r" % (vp[1]["persistence"], vp[2]["persistence"], vp[3]["display"]))
check("zoom at step 8 is four times, and lane one's scale at its fourth detent is -12 dB",
      vp[4]["zoom"] == 4 and vp[5]["channels"][0]["fsDb"] == -12, "%r %r" % (vp[4]["zoom"], vp[5]["channels"][0]["fsDb"]))
check("the lag and then mid and side: the one thrown last wins", vp[6]["lagOn"] is True and vp[7]["midSide"] is True
      and vp[7]["lagOn"] is False)
check("X on lane two makes the pair two against one, never one lane twice, and the trigger takes lane two",
      vp[8]["xy"] == [1, 0] and vp[9]["trigSource"] == 1, "%r %r" % (vp[8]["xy"], vp[9]["trigSource"]))
check("the reticle goes where it is put, held to the screen, and the photocell's button turns it on",
      vph[10]["u"] == 0.25 and vph[10]["v"] == 0.6 and vph[11]["u"] == 1 and vph[11]["v"] == 0 and vph[12]["on"] is True,
      "%r %r %r" % (vph[10], vph[11], vph[12]))
check("a filter's kind, a beam level the menu has not got, the input's side, and a timebase",
      vp[13]["filter"]["type"] == "notch" and vp[14]["beam"] == "" and vp[15]["analyseAt"] == "pre" and vp[16]["timebase"] == 7,
      "%r %r %r %r" % (vp[13]["filter"]["type"], vp[14]["beam"], vp[15]["analyseAt"], vp[16]["timebase"]))
# The comparison, against the port given one hand differently.
vwrong = [l.replace('"value": 8}', '"value": 9}') if '"zoom"' in l else l for l in vlines]
vpath = os.path.join(BUILD, "view_wrong.txt")
with open(vpath, "w", encoding="utf-8") as f: f.write("\n".join(vwrong) + "\n")
vwport = subprocess.run([rexe, vpath, rsources], check=True, capture_output=True, text=True).stdout.strip().split("\n")
check("and the comparison fails against a zoom a step further", bool(rbad(vpg, vwport)))

print("\n--- the generator in WebAssembly ---")
# Stage 5a: the core's generator compiled for the browser, the module the page
# carries, driven through the page's own `makeWasmCore` - the bridge the
# worklet uses - and held to the page's JavaScript generator driven the same
# way, run for run, through what the worklet reads back of a core: the
# samples, the envelope, the crossings, the budget, the drawing, and the
# oscillators as each left them. The same runs as the whole generator's, the
# effect's among them, which the effects worklet runs.
WBUILD = os.path.join(CORE, "wasm", "build.py")
WSRC = os.path.join(CORE, "wasm", "scope_wasm.cpp")
GEN_JS = os.path.join(HERE, "tools", "generator_js.mjs")
def wrun(mode, path=listed, module=None, pairs=None):
    env = dict(os.environ, CORE=mode)
    if module: env["WASM_FILE"] = module
    if pairs: env["PAIRS"] = pairs
    return subprocess.run(["node", GEN_JS, path], env=env, check=True, capture_output=True, text=True).stdout.splitlines()
def wworst(js, wa):
    by = {}
    for (name, _), a, b in zip(runs, js, wa):
        family = name.split("-")[0]
        by[family] = max(by.get(family, 0.0), worst(row(a), row(b)))
    return by
fresh = subprocess.run([sys.executable, WBUILD, "--check"], capture_output=True, text=True)
check("the page carries this core, compiled", fresh.returncode == 0, (fresh.stdout + fresh.stderr).strip()[-300:])
wjs, wwa = wrun("js"), wrun("wasm")
fxed = [n for n, r in runs if "fx 1" in r]
check("every run answered by both, the effect's included: %d runs, %d of the effect" % (len(runs), len(fxed)),
      len(wjs) == len(wwa) == len(runs) and len(fxed) >= 4)
wby = wworst(wjs, wwa)
for family in sorted(wby):
    check("compiled, %s, the same to %g" % (family, TOL), wby[family] <= TOL, "worst %.3g" % wby[family])
# The main thread's call (5c): the picture pair only, the heard pair and B's
# handed over as none, as the JavaScript core is handed null.
pjs, pwa = wrun("js", pairs="picture"), wrun("wasm", pairs="picture")
pby = wworst(pjs, pwa)
check("compiled, asked for the picture alone as the main thread asks, every family the same to %g" % TOL,
      len(pjs) == len(pwa) == len(runs) and max(pby.values()) <= TOL, "worst %.3g" % max(pby.values()))
bjs, bwa = wrun("js", pairs="b"), wrun("wasm", pairs="b")
bby = wworst(bjs, bwa)
check("and asked for the picture and B's pair as the tone source asks, every family the same to %g" % TOL,
      len(bjs) == len(bwa) == len(runs) and max(bby.values()) <= TOL, "worst %.3g" % max(bby.values()))
heardless = [n for (n, r), a, b in zip(runs, wjs, pjs) if "fx 1" not in r and worst(row(a), row(b)) > 0]
check("and asked for the picture alone, a run with a heard pair or a layer B reads as one without",
      len(heardless) >= len(runs) // 2, "%d runs" % len(heardless))
# Nulls. The check of the page's copy, against a copy of the page with one
# character of the module changed.
wpage = os.path.join(BUILD, "scope_wasm_wrong.html")
page_text = open(os.path.join(CORE, "..", "web", "scope.html"), encoding="utf-8").read()
wat = page_text.index("/* WASM_CORE_BEGIN */") + 30000
with open(wpage, "w", encoding="utf-8") as f: f.write(page_text[:wat] + ("B" if page_text[wat] != "B" else "C") + page_text[wat + 1:])
check("and the page's copy is told from a module one character different",
      subprocess.run([sys.executable, WBUILD, "--check", "--page", wpage], capture_output=True).returncode != 0)
# And the comparison, against modules built from the bridge with one thing
# wrong in each: a route a thousandth too strong, the oscillators' phases not
# handed back, a setting given as text dropped.
def wnull(what, old, new):
    src = open(WSRC).read()
    assert src.count(old) == 1, old
    bad_src, bad_mod = os.path.join(BUILD, "scope_wasm_null.cpp"), os.path.join(BUILD, "scope_wasm_null.wasm")
    with open(bad_src, "w") as f: f.write(src.replace(old, new))
    subprocess.run([sys.executable, WBUILD, "--source", bad_src, "--out", bad_mod], check=True)
    by = wworst(wjs, wrun("wasm", module=bad_mod))
    check("and the comparison fails against a module with %s" % what, max(by.values()) > TOL,
          ", ".join(f for f in sorted(by) if by[f] > TOL))
wnull("a route a thousandth too strong", "route.amount = r[4];", "route.amount = r[4] * 1.001;")
wnull("the oscillators' phases not handed back", "{ l.phase, l.held, l.value }", "{ 0.0, l.held, l.value }")
wnull("the heard pair withheld from a caller who gave one", "const bool heard = given & 2, pairB = given & 4;",
      "const bool heard = false, pairB = given & 4;")
wnull("a setting given as text dropped",
      "else if (v.type == T::String) core->set(field, std::string_view(scope::utf16To8(v.s)), layer);", "")
# And the effect's own: a module that hands the input back without running
# the effect. Every effect run has to fail it - the one with nothing on too,
# by its oscillators, which the effect steps and the copy does not.
def wnull_effect():
    old = "core->effect(l, l + m, l + 2 * m, l + 3 * m, n);"
    new = "(void)n; for (std::size_t i = 0; i < 2 * m; i++) l[2 * m + i] = l[i];"
    src = open(WSRC).read()
    assert src.count(old) == 1, old
    bad_src, bad_mod = os.path.join(BUILD, "scope_wasm_null.cpp"), os.path.join(BUILD, "scope_wasm_null.wasm")
    with open(bad_src, "w") as f: f.write(src.replace(old, new))
    subprocess.run([sys.executable, WBUILD, "--source", bad_src, "--out", bad_mod], check=True)
    bad = wrun("wasm", module=bad_mod)
    off = [n for (n, _), a, b in zip(runs, wjs, bad) if n.startswith("effect") and worst(row(a), row(b)) > TOL]
    check("and every effect run fails against a module that hands the input back", sorted(off) == sorted(fxed), ", ".join(off))
wnull_effect()

print("\n--- the instrument, compiled (5f) ---")
# The plugin's instrument whole (scope/instrument.h) - brain and engine, as
# the plugin plays it - natively, and as the page carries it compiled, played
# through the page's own wrapper (makeWasmBrain, which the site's worklet
# runs). The same script into each: setups, the page's hands, notes and MIDI
# clock as bytes, blocks of every size. Out: the heard pair and the picture
# pair a sample at a time, what went to a MIDI port, refusals, and the state
# code the page is shown. Held to equality, not to a tolerance: the two are
# the same code, and every run so far comes out the same to the last bit of
# every float - a tolerance would only be somewhere for a difference to hide.
iexe = build("instrument_cpp")
inames = [n for n in subprocess.run([iexe, "--names"], check=True, capture_output=True, text=True).stdout.split("\n") if n]
icode = dict(zip(inames, subprocess.run([iexe, "--code", *inames], check=True, capture_output=True, text=True).stdout.split("\n")))
def iscript(name, lines):
    path = os.path.join(BUILD, "instrument_%s.txt" % name)
    with open(path, "w") as f: f.write("\n".join(_json.dumps(l) for l in lines) + "\n")
    return path
def icpp(path): return subprocess.run([iexe, path], check=True, capture_output=True, text=True).stdout.split("\n")
def ijs(path, module=None):
    env = dict(os.environ, **({"WASM_FILE": module} if module else {}))
    return subprocess.run(["node", os.path.join(HERE, "tools", "instrument_js.mjs"), path], env=env,
                          check=True, capture_output=True, text=True).stdout.split("\n")
# The worst sample apart, and the first line that is not a block and differs.
# Each sample read back as the float it is: nine digits round-trip a float,
# but a float that is a tie at nine digits (0.1376953125) is written
# ...312 by the C library, which breaks ties to even, and ...313 by
# JavaScript's toPrecision, which breaks them upwards - the same sample.
from array import array
def ifloats(line): return array("f", [float(v) for v in line.split()[1:]]).tolist()
check("and the comparison reads a tie written two ways as one float, and the next float as another",
      ifloats("block 0.137695312") == ifloats("block 0.137695313") != ifloats("block 0.137695328"))
def icompare(a, b):
    if len(a) != len(b): return inf, "%d lines against %d" % (len(a), len(b))
    most, other = 0.0, ""
    for i, (x, y) in enumerate(zip(a, b)):
        if x.startswith("block ") and y.startswith("block "):
            most = max(most, worst(ifloats(x), ifloats(y)))
        elif x != y and not other: other = "line %d: %s | %s" % (i, x[:70], y[:70])
    return most, other
def blocks(k, n=128, stride=1): return [["block", n, stride]] * k
NOTE_ON = lambda n, v=100: ["midi", 0x90, n, v]
NOTE_OFF = lambda n: ["midi", 0x80, n, 0]

iruns = {}
iruns["notes"] = [["make", 48000, 128, icode["Harmonic tone"]]] + blocks(3) + [NOTE_ON(57)] + blocks(30) \
    + [NOTE_ON(64, 70)] + blocks(20) + [["midi", 0xB0, 64, 127], NOTE_OFF(57), NOTE_OFF(64)] + blocks(20) \
    + [["midi", 0xB0, 64, 0]] + blocks(30) + [NOTE_ON(45), ["midi", 0xB0, 123, 0]] + blocks(10)
FADE = _json.dumps({"mode": "both", "envs": [{"delay": 0, "attack": 0.3, "attackMid": 0.5, "decay": 0.5, "decayMid": 0.5,
                    "sustain": 1, "release": 0.4, "releaseMid": 0.5, "restart": True, "loop": False}] * 2})
iruns["hands"] = [["make", 44100, 128, icode["Harmonic tone"]], NOTE_ON(57)] + blocks(10) \
    + [["slider", "amp", "30"]] + blocks(10) + [["control", "planeKaleido", "6"]] + blocks(10) \
    + [["control", "crossOn", True], ["click", "planeOS4"]] + blocks(10) \
    + [["routings", "lfo1>gen.vcf@0.55;lfo1>gen.freq@0.35"]] + blocks(20) + [["fade", FADE]] + blocks(10) \
    + [["control", "genMode", "harmonograph"]] + blocks(20) + [["click", "midiPoly"], NOTE_ON(60), NOTE_ON(64)] + blocks(20) \
    + [["slider", "lfoRate1", "300"], ["click", "dispXY"], ["control", "persistence", "0.3"], ["click", "photoButton"]] \
    + blocks(40) + [["control", "macroName1", "Brückner — 🎹"], ["click", "clearButton"]] + blocks(10)
iruns["refused"] = [["make", 48000, 128, "not a code at all"]] + blocks(4) + [["slider", "noSuchSlider", "1"],
    ["setup", "eyJub3QiOg=="], ["fade", "{not json"], ["slider", "amp", "20"]] + blocks(4)
# Every preset in turn, a note held through each, so whatever a preset leaves
# behind is what the next one is loaded over, as a player's evening goes.
iruns["presets"] = [["make", 48000, 128, icode["Harmonic tone"]]]
for n in inames:
    iruns["presets"] += [["setup", icode[n]], NOTE_ON(57)] + blocks(10, 128, 7) + [NOTE_OFF(57)] + blocks(3, 128, 7)
# The arpeggiator stepping on MIDI clock, and what it sends out of the port.
iruns["clock"] = [["make", 48000, 128, icode["Arpeggiated chords"]], ["midi", 0xFA], NOTE_ON(60), NOTE_ON(64), NOTE_ON(67)]
for k in range(400): iruns["clock"] += ([["midi", 0xF8]] if k % 2 == 0 else []) + [["block", 128, 5]]
iruns["clock"] += [["midi", 0xFC], NOTE_OFF(60), NOTE_OFF(64), NOTE_OFF(67)] + blocks(40, 128, 5)
# A loop through the picture: the photocell reads the grid the instrument
# draws for itself, at sixty frames a second of audio time, and bends the sound.
iruns["photocell"] = [["make", 48000, 256, icode["Pendulums bent by the light"]], NOTE_ON(57)] + blocks(500, 256, 9)
# A clock byte alone, after a note: one byte and not three, since two more
# would be data under the note's running status - a note-on for note nought
# at velocity nought, which lets go of a note nought held.
iruns["realtime"] = [["make", 48000, 128, icode["Harmonic tone"]], NOTE_ON(0), NOTE_ON(57)] + blocks(10) \
    + [["midi", 0xF8], ["midi", 0xFA]] + blocks(20) + [["midi", 0xF8]] + blocks(10)
# The input (5g): a saw of a hundred samples on the left and a triangle of
# seventy-three on the right, made by arithmetic on both sides. Drawn, it
# goes through the plane - the kaleidoscope, then the twist under a routing -
# and a preset loaded meanwhile leaves it drawn; given to the generator, it
# moves a figure by each of its three modes; mono, and then none at all.
def icode_of(setup):
    return base64.b64encode(_json.dumps(dict(setup, v=4)).encode()).decode().rstrip("=")
iruns["input"] = [["make", 48000, 128, icode["Harmonic tone"]], ["feed", 100, 73], NOTE_ON(57)] + blocks(6) \
    + [["click", "srcMic"]] + blocks(10) + [["control", "planeKaleido", "6"]] + blocks(10) \
    + [["routings", "lfo1>gen.twist@0.5"]] + blocks(20) + [["setup", icode["Pluck"]]] + blocks(10) \
    + [["click", "srcTone"], ["control", "genMode", "figure"], ["control", "inputMode", "1"]] + blocks(20) \
    + [["control", "inputMode", "2"]] + blocks(20) + [["control", "inputMode", "3"]] + blocks(30) \
    + [["feed", 64], ["click", "srcMic"]] + blocks(10) + [["feed"]] + blocks(10)
# A state that opens with the input drawn, as a project reopened does.
iruns["opened"] = [["make", 44100, 128, icode_of({"timebase": 3, "pluginInput": True})], ["feed", 90, 61]] + blocks(10) \
    + [["click", "srcTone"], NOTE_ON(60)] + blocks(10)
# A rack (5i): four lanes of the page's, then five with the generator's
# first and a note in it, the trigger moved off the generator's lane and the
# pair set across two lanes; a preset loaded meanwhile; back to the generator
# for longer than the ring holds, so the last blocks read rows the rack wrote
# once - which the pair has to have cleared of its lanes.
iruns["rack"] = [["make", 48000, 128, icode["Harmonic tone"]], ["feedlanes", 100, 73, 51, 37, 29]] + blocks(2) \
    + [["control", "srcLanes", "4,-1"]] + blocks(8) + [["control", "srcLanes", "5,0"], NOTE_ON(57)] + blocks(10) \
    + [["click", "trigSource2"], ["control", "xyY", "3"]] + blocks(10) + [["setup", icode["Pluck"]]] + blocks(6) \
    + [["control", "srcLanes", "4,-1"], NOTE_ON(60)] + blocks(6) + [["click", "srcTone"]] + blocks(40)
iruns["sizes"] = [["make", 96000, 128, icode["Pluck"]], NOTE_ON(50)] + [["block", n] for n in (1, 64, 300, 127, 129, 2048, 5)] * 4

iout = {}
for name, lines in iruns.items():
    path = iscript(name, lines)
    a, b = icpp(path), ijs(path)
    iout[name] = (path, a, b)
    most, other = icompare(a, b)
    said = sum(1 for l in a if l.startswith("state ")), sum(1 for l in a if l.startswith("out ")), sum(1 for l in a if l == "no")
    check("%s: the compiled instrument is the native one, every sample, every state and every message out" % name,
          most == 0 and not other, "worst %g; %d states, %d sends, %d refusals%s" % (most, said[0], said[1], said[2],
                                                                                    ("; " + other) if other else ""))
# What the runs have to have had in them for the checks above to mean anything.
def icount(name, prefix): return sum(1 for l in iout[name][1] if l.startswith(prefix))
def ipeak(name): return max((abs(float(v)) for l in iout[name][1] if l.startswith("block ") for v in l.split()[1:]), default=0)
check("and the runs had sound in them, states that changed, MIDI sent and refusals said",
      all(ipeak(n) > 0.05 for n in iruns if n != "refused") and icount("hands", "state ") >= 8
      and icount("clock", "out ") >= 10 and icount("refused", "no") == 4 and icount("presets", "state ") >= len(inames),
      "peaks %s; hands states %d, clock sends %d, refusals %d, preset states %d" % (
          {n: round(ipeak(n), 3) for n in iruns}, icount("hands", "state "), icount("clock", "out "),
          icount("refused", "no"), icount("presets", "state ")))
# And what the input runs played, read off the samples, since two sides that
# both ignored the input would agree perfectly: drawn with nothing on the
# plane, the heard pair is the input exactly - the run's blocks seven to
# sixteen, and the reopened run's first ten - and folded by the kaleidoscope
# it is not; drawing the generator, it is not the input either.
def ifed(k, pl, pr):
    t, u = (k % pl) / pl, (k % pr) / pr
    return array("f", [0.5 * (2 * t - 1), 0.5 * (4 * u - 1 if u < 0.5 else 3 - 4 * u)]).tolist()
def iheard(name, first, count, pl, pr, start):
    rows = [ifloats(l) for l in iout[name][1] if l.startswith("block ")][first:first + count]
    most = 0.0
    for b, row in enumerate(rows):
        for k in range(128):
            want = ifed(start + (b * 128) + k, pl, pr)
            most = max(most, abs(row[k] - want[0]), abs(row[128 + k] - want[1]))
    return most
drawn_plain, drawn_open = iheard("input", 7, 9, 100, 73, 7 * 128), iheard("opened", 0, 10, 90, 61, 0)
folded, generated = iheard("input", 17, 9, 100, 73, 17 * 128), iheard("input", 5, 1, 100, 73, 5 * 128)
check("and the input drawn is heard as it was fed, the reopened state's from its first block, and not once folded or under the generator",
      drawn_plain == 0 and drawn_open == 0 and folded > 0.1 and generated > 0.1,
      "drawn %g and %g; folded %g, generator %g" % (drawn_plain, drawn_open, folded, generated))
check("and the reading fails against the input a sample late", iheard("input", 7, 9, 100, 73, 7 * 128 + 1) > 0)
# A rack's lanes, read off the samples: each of the page's lanes the input it
# was fed, at its own index; the generator's lane what the generator plays
# (Harmonic tone, whose heard pair is its picture pair); nothing past the
# count; and back at the generator, two lanes again.
def irack(row, lane): return row[(2 + lane) * 128:(3 + lane) * 128]
def isaw(k, p): return array("f", [0.5 * (2 * ((k % p) / p) - 1)]).tolist()[0]
rrows = [ifloats(l) for l in iout["rack"][1] if l.startswith("block ")]
def ilane_fed(b, lane, period, fed_lane=None):
    return max(abs(irack(rrows[b], lane)[k] - isaw(b * 128 + k, period)) for k in range(128))
four = max(ilane_fed(b, c, p) for b in range(3, 10) for c, p in enumerate([100, 73, 51, 37]))
past = max(abs(v) for b in range(3, 10) for c in (4, 5) for v in irack(rrows[b], c))
five = max(ilane_fed(b, c, p) for b in range(12, 20) for c, p in ((1, 73), (2, 51), (3, 37), (4, 29)))
synth = max(abs(irack(rrows[b], 0)[k] - rrows[b][k]) for b in range(12, 20) for k in range(128))
synth_peak = max(abs(v) for b in range(12, 20) for v in irack(rrows[b], 0))
after = max(abs(v) for b in range(len(rrows) - 4, len(rrows)) for c in (2, 3, 4, 5) for v in irack(rrows[b], c))
check("and a rack's lanes are what they were fed at their own places, the generator's lane the generator, nothing past the count",
      four == 0 and past == 0 and five == 0 and synth == 0 and synth_peak > 0.1 and after == 0,
      "fed %g and %g, past %g, generator %g at %.3f, after %g" % (four, five, past, synth, synth_peak, after))
check("and the reading fails against the lanes one place along", ilane_fed(15, 2, 73) > 0)
# A rack with no generator lane, a note held: nothing of the generator heard.
# Its blocks counted from the start - 2, 8, 10, 10 and 6 before it - since the
# run after it is as long as it has to be to wrap the ring.
unheard = max(abs(v) for b in range(37, 42) for v in rrows[b][:256])
check("and a rack with no generator lane sends nothing out, a note held or not", unheard == 0, "peak %g" % unheard)
# Nulls. The comparison one line out of step; a native run with one hand a
# step away; and modules from the bridge with one thing wrong in each.
pa, ca, ja = iout["notes"]
check("and the comparison fails one line out of step", icompare(ca[1:] + [""], ja)[0] > 0)
moved = [l if l != ["slider", "amp", "30"] else ["slider", "amp", "31"] for l in iruns["hands"]]
check("and against the native run with the level moved to 31 rather than 30",
      icompare(icpp(iscript("hands_moved", moved)), iout["hands"][2]) != (0.0, ""))
def inull(what, old, new, runs):
    src = open(WSRC).read()
    assert src.count(old) == 1, old
    bad_src, bad_mod = os.path.join(BUILD, "scope_wasm_null.cpp"), os.path.join(BUILD, "scope_wasm_null.wasm")
    with open(bad_src, "w") as f: f.write(src.replace(old, new))
    subprocess.run([sys.executable, WBUILD, "--source", bad_src, "--out", bad_mod], check=True)
    seen = [n for n in runs if icompare(iout[n][1], ijs(iout[n][0], bad_mod)) != (0.0, "")]
    check("and the comparison fails against a module with %s" % what, seen == runs, ", ".join(seen))
inull("the input's lanes the wrong way round",
      "const scope::Instrument::Input input { brainInput.data(), count >= 2 ? brainInput.data() + frames : nullptr, inputLanes.data(), count };",
      "const scope::Instrument::Input input { count >= 2 ? brainInput.data() + frames : brainInput.data(), count >= 2 ? brainInput.data() : nullptr, inputLanes.data(), count };",
      ["input", "opened"])
inull("a stereo input taken as mono", "brainInput.data(), count >= 2 ? brainInput.data() + frames : nullptr, inputLanes.data(), count }",
      "brainInput.data(), nullptr, inputLanes.data(), count }", ["input", "opened"])
inull("a rack's lanes handed over one place along",
      "inputLanes[static_cast<std::size_t>(c)] = brainInput.data() + static_cast<std::size_t>(c) * frames;",
      "inputLanes[static_cast<std::size_t>(c)] = brainInput.data() + static_cast<std::size_t>((c + 1) % count) * frames;", ["rack"])
inull("every message padded to three bytes", "std::clamp(length, 1, 3)", "std::clamp(length, 3, 3)", ["realtime"])
inull("the page's MIDI dropped", "  midiLengths.push_back(n);\n", "  midiIn.resize(midiIn.size() - n);\n", ["notes", "clock"])
# Only the sweep can see this one: the presets the other runs play make a
# heard pair that is the picture pair, sample for sample, as most of the
# plain waves do; 265 of the 281 presets do not.
inull("the heard pair handed back as the picture pair",
      "    instrument->latestLane(c, lanes + (2 + static_cast<std::size_t>(c)) * frames, frames);",
      "    if (c >= 2) instrument->latestLane(c, lanes + (2 + static_cast<std::size_t>(c)) * frames, frames);"
      " else std::copy(lanes + c * frames, lanes + (c + 1) * frames, lanes + (2 + c) * frames);", ["presets"])
inull("a state never published", "  if (!instrument->changed()) return -1;", "  return -1;", ["hands", "presets"])
inull("a switch read as off", "scope::Json::boolean(kind == 2)", "scope::Json::boolean(false)", ["hands"])

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the C++ core is the page's, sample for sample")
