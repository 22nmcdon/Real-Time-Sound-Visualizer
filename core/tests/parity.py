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
    by_name[name] = max(by_name.get(name, 0.0), w)
    if w > worst_line[1]: worst_line = (call[:80], w)
check("every call answered by both: %d calls" % len(lines), len(js_rows) == len(cpp_rows) == len(lines),
      "%d from the page, %d from the port" % (len(js_rows), len(cpp_rows)))
for name in sorted(by_name):
    check("%s, the same to %g" % (name, TOL), by_name[name] <= TOL, "worst %.3g" % by_name[name])
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
check("and against a pulse of 0.3 answered as one of 0.31",
      worst(row(subprocess.run(["node", os.path.join(HERE, "tools", "functions_js.mjs"),
                                _one(lines[pulse][:-3] + "0.31")], check=True, capture_output=True, text=True).stdout),
            row(cpp_rows[pulse])) > 1e-6)

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the C++ core is the page's, sample for sample")
