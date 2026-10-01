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
check("and against a pulse of 0.3 answered as one of 0.31",
      worst(row(subprocess.run(["node", os.path.join(HERE, "tools", "functions_js.mjs"),
                                _one(lines[pulse][:-3] + "0.31")], check=True, capture_output=True, text=True).stdout),
            row(cpp_rows[pulse])) > 1e-6)

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the C++ core is the page's, sample for sample")
