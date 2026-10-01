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
import os, subprocess, sys, glob

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

def worst(a, b):
    if len(a) != len(b): return float("inf")
    return max((abs(x - y) for x, y in zip(a, b)), default=0.0)

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
    path = "P:-0.5,0.2,0.3,0.8,0.9,-0.4,-0.1,-0.7,-0.5,0.2;0,0.18,0.5,0.5,0.86,1"
    for t in ts + [3.4, 0.5, 0.18]:
        for name in ("Text", "Path", "Drawn"):
            out.append("figureAt %s %r 5 %s" % (name, t, path))
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
    add("dyad-wavetable", [(0, "set shape wavetable"), (0, "wavetable " + bank), (0, "routes " + route(TABLE, 0.8, index=1))])
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
                        (0, "figPath P:-0.5,0.2,0.3,0.8,0.9,-0.4,-0.1,-0.7,-0.5,0.2;0,0.18,0.5,0.5,0.86,1"),
                        (0, "set figureRate 90")])
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
# (swing, pendulum, three turns, facing), and the voices on each layer.
TAIL = 22
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
        elif r < 0.70: out.append("draw %d %d %s" % (krng.randint(0, 1), krng.randint(1, 9), krng.choice(["outer", "lowest", "highest", "recent"])))
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

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the C++ core is the page's, sample for sample")
