"""The sound audit (24 Nov): does every control that changes the sound move it somewhere of its own?

The owner's question: "most of the settings and sound changes available here all
head toward the same sound and goal; a lot of things achieve a similar result to a
bitcrusher". A hypothesis to test, not to assume: Drive, Fold, Bits, Rate, the
Plane's Snap, high Scan and the Picture amount and Swell all move the sound the
same way (brighter, buzzier, stepped or aliased); only the voice filter and the EQ
take anything away; and nothing goes darker-smoother, noisier, inharmonic or
percussive beyond the envelopes.

Everything here is rendered through the core offline (render_cpp, the instrument
as the plugin and the site play it, the same to the bit every run). Four bases -
the base the instrument opens on (a still sine), the base with the saw, and two of
the bank as shipped, the Tine piano (a pluck) and the Slow pad - each with one
control at a time set to about six places across its range, a held A3 and a short
phrase. Every preset as shipped is rendered too, as a point.

Each render is measured on the same features (FEATURES below, with how each is
read). The one that needed care is aliasing: a bitcrusher's steps fold harmonics
past the Nyquist back down to frequencies that are not harmonics of the note, but
so does an FM pair at 5:4, on purpose. The two are told apart by rendering the held
note twice, on A3 and a fourth up: a partial the sound is made of follows the
note (an FM bell's 1.4 is 1.4 times either), and one folded back by a sample rate -
the host's, or Rate's own hold - does not. Validated (`--validate`, and
the page) on a numpy bitcrusher and a clean band-limited saw, an FM bell, white
noise, and the instrument's own Bits and saw.

A smooth Scan (step 4 of the brief) is prototyped here only, never in the
instrument: scan.h copied into the build directory with its read changed, and
render_cpp built against the copy (SMOOTH below).

    python3 web/docs/listening/sound-audit/render.py              render, measure, write results.json
    python3 web/docs/listening/sound-audit/render.py --validate   the aliasing measure's checks alone
    python3 web/docs/listening/sound-audit/analyse.py             the effects, groups and gaps: analysis.json
    python3 web/docs/listening/sound-audit/audio.py               the MP3s

Renders are cached by their script (core/build/audit/cache.json), so a rerun after
a change to the measures alone renders nothing... except it does: the cache holds
features, not audio, so a change to a measure needs `--fresh`.
"""
import base64, hashlib, json, os, re, shutil, subprocess, sys
from multiprocessing import Pool
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
CORE = os.path.join(ROOT, "core")
BUILD = os.path.join(CORE, "build", "audit")
os.makedirs(BUILD, exist_ok=True)
CACHE = os.path.join(BUILD, "cache.json")

# ---------------------------------------------------------------- the renderers

def build(name, include):
    out = os.path.join(BUILD, name)
    src = os.path.join(CORE, "tests", "tools", "render_cpp.cpp")
    if not os.path.exists(out) or os.path.getmtime(out) < max(os.path.getmtime(src), newest(include)):
        subprocess.run(["g++", "-std=c++17", "-O2", "-I", include, src, "-o", out], check=True)
    return out

def newest(d):
    return max(os.path.getmtime(os.path.join(r, f)) for r, _, fs in os.walk(d) for f in fs)

# The smooth Scan's prototypes, each a change to a copy of scan.h. What Scan does
# now: the picture's 64x64 grid, blurred by the Softness, read at 256 points round
# a circle by bilinear interpolation between cell centres, turned into 64
# harmonics and a new table sixty times a second.
#   interp   the read bicubic (Catmull-Rom) over the whole blurred grid, in place of
#            bilinear over four cells: no kinks where the circle crosses a cell edge
#   taper    the 64 harmonics rolled off (a Gaussian falling to a tenth by the 32nd),
#            so the corners the grid leaves in the read are not heard as top end
#   time     each read averaged with the last (a one-pole at a third), so the table
#            does not jump a whole frame's change sixty times a second
#   smooth   all three
SMOOTH = {
    "interp": ["INTERP"], "taper": ["TAPER"], "time": ["TIME"], "smooth": ["INTERP", "TAPER", "TIME"],
}

SCAN_PATCH = [
    # the read: bicubic over the whole blur when INTERP
    ("""    scanBlurRead(grid, n, soft, path, rows_.data(), blurred_.data(), rowAt_.data(), outAt_.data(), stamp_);
    scanRead(blurred_.data(), n, path, points);
    return true;""",
     """#ifdef AUDIT_INTERP
    scanBlur(grid, n, soft, rows_.data(), blurred_.data());
    scanReadPlaces(n, path, [&](std::size_t i, double u, double v) { points[i] = auditBicubic(blurred_.data(), n, u, v); });
#else
    scanBlurRead(grid, n, soft, path, rows_.data(), blurred_.data(), rowAt_.data(), outAt_.data(), stamp_);
    scanRead(blurred_.data(), n, path, points);
#endif
#ifdef AUDIT_TIME
    if (auditHad_[auditWhich_]) for (std::size_t i = 0; i < kScanPoints; i++) points[i] = auditLast_[auditWhich_][i] + (points[i] - auditLast_[auditWhich_][i]) / 3;
    auditLast_[auditWhich_] = points; auditHad_[auditWhich_] = true;
#endif
    return true;"""),
    ("""  std::uint32_t stamp_ = 0;
  std::array<std::array<double, kScanPoints>, 2> readings_ {};""",
     """  std::uint32_t stamp_ = 0;
  std::array<std::array<double, kScanPoints>, 2> auditLast_ {};
  std::array<bool, 2> auditHad_ { { false, false } };
  std::size_t auditWhich_ = 0;
  std::array<std::array<double, kScanPoints>, 2> readings_ {};"""),
    # which picture the reading is for, so TIME keeps one memory a picture
    ("""      if (paths[p] && !frozen) read_[p] = read(pic.grid, pic.length, *paths[p], soft, readings_[p]);""",
     """      auditWhich_ = p;
      if (paths[p] && !frozen) read_[p] = read(pic.grid, pic.length, *paths[p], soft, readings_[p]);"""),
    # the taper on the harmonics
    ("""    a[k] = 2 * sa / n; b[k] = 2 * sb / n;
  }""",
     """    a[k] = 2 * sa / n; b[k] = 2 * sb / n;
#ifdef AUDIT_TAPER
    const double g = std::exp(-std::log(10.0) * (static_cast<double>(k) / 32) * (static_cast<double>(k) / 32));
    a[k] *= g; b[k] *= g;
#endif
  }"""),
    # the bicubic itself, after scanBilinear
    ("""// The path read: kScanPoints brightnesses""",
     """inline double auditBicubic(const double* g, int n, double u, double v) {
  const double fx = u * n - 0.5, fy = v * n - 0.5;
  const double x0 = std::floor(fx), y0 = std::floor(fy), tx = fx - x0, ty = fy - y0;
  const auto cell = [&](double cx, double cy) {
    return cx < 0 || cy < 0 || cx >= n || cy >= n ? 0.0 : g[static_cast<int>(cy) * n + static_cast<int>(cx)];
  };
  const auto cr = [](double p0, double p1, double p2, double p3, double t) {
    return 0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t * t * t);
  };
  double col[4];
  for (int j = 0; j < 4; j++) {
    const double yy = y0 - 1 + j;
    col[j] = cr(cell(x0 - 1, yy), cell(x0, yy), cell(x0 + 1, yy), cell(x0 + 2, yy), tx);
  }
  return std::max(0.0, cr(col[0], col[1], col[2], col[3], ty));
}

// The path read: kScanPoints brightnesses"""),
]

def smooth_include(variant):
    """A copy of core/include with scan.h changed for one variant, the defines written at its top."""
    inc = os.path.join(BUILD, "include-" + variant)
    scan = os.path.join(inc, "scope", "scan.h")
    if os.path.exists(inc) and os.path.getmtime(scan) >= newest(os.path.join(CORE, "include")) and os.path.getmtime(scan) >= os.path.getmtime(__file__):
        return inc
    shutil.rmtree(inc, ignore_errors=True)
    shutil.copytree(os.path.join(CORE, "include"), inc)
    s = open(scan).read()
    for old, new in SCAN_PATCH:
        assert s.count(old) == 1, ("scan.h anchor", old[:60])
        s = s.replace(old, new)
    s = s.replace("#pragma once", "#pragma once\n" + "".join("#define AUDIT_%s 1\n" % d for d in SMOOTH[variant]), 1)
    open(scan, "w").write(s)
    return inc

RENDER = {"core": build("render_cpp", os.path.join(CORE, "include"))}
for v in SMOOTH: RENDER[v] = build("render_" + v, smooth_include(v))

# ---------------------------------------------------------------- the sounds

def code_of(fields):
    return base64.b64encode(json.dumps(dict({"v": 15}, **fields), separators=(",", ":")).encode()).decode().rstrip("=")

def bank():
    s = open(os.path.join(CORE, "include", "scope", "presets.h")).read()
    lib = json.loads("".join(re.findall(r'R"preset\((.*?)\)preset"', s, re.S)))
    base = json.loads(re.search(r'R"base\((.*?)\)base"', s, re.S).group(1))
    return [(sec[0], e[0], e[1]) for sec in lib for e in sec[1]], base

PRESETS, BASE = bank()
PRESET = {name: setup for _, name, setup in PRESETS}
BASES = {
    "sine": ("Sine (the base)", BASE),
    "saw": ("Saw (the base, Saw)", dict(BASE, shape="ramp")),
    "pluck": ("Tine piano (bank)", PRESET["Tine piano"]),
    "pad": ("Slow pad (bank)", PRESET["Slow pad"]),
}

# Every control included, with its places and what has to be on for it to act
# (`needs`: laid over the base for every place, the control's own rest included,
# so its path starts from the module switched on at its rest). `rest` is where the
# path starts: the control's default, or the needs' value. `two` splits a control
# that goes both ways from its rest into two paths. Ranges are the schema's.
def lin(a, b, n=6): return [round(a + (b - a) * i / (n - 1), 3) for i in range(n)]

CONTROLS = [
    # id, group, name, places, rest, needs, two
    # The generator
    ("amp", "Generator", "Level", lin(10, 100), 55, {}, False),
    ("phase", "Generator", "Phase", lin(0, 180), 90, {}, True),
    ("glide", "Generator", "Glide", [0, 20, 60, 150, 300, 600], 0, {}, False),
    ("just", "Generator", "Tuning (just)", [False, True], True, {}, False),
    # The amp envelope
    ("atk", "Amp envelope", "Attack", [1, 10, 50, 200, 600, 1500], None, {}, False),
    ("dec", "Amp envelope", "Decay", [20, 80, 250, 600, 1500, 4000], None, {}, False),
    ("sus", "Amp envelope", "Sustain", lin(0, 100), None, {}, False),
    ("rel", "Amp envelope", "Release", [10, 80, 250, 600, 1500, 4000], None, {}, False),
    ("envDelay", "Amp envelope", "Delay", [0, 20, 60, 150, 300, 600], 0, {}, False),
    ("envHold", "Amp envelope", "Hold", [0, 50, 150, 400, 1000, 2500], 0, {}, False),
    # The voice filter, switched to Low pass where a base has it off
    ("vcfType", "Voice filter", "Type", [0, 1, 2, 3, 4], 0, {}, False),
    ("vcfCut", "Voice filter", "Cutoff", lin(0, 1000), 667, {"vcfType": 1}, False),
    ("vcfRes", "Voice filter", "Resonance", lin(0, 100), 0, {"vcfType": 1, "vcfCut": 500}, False),
    ("vcfTrack", "Voice filter", "Key track", lin(0, 100), 0, {"vcfType": 1, "vcfCut": 500}, False),
    ("vcfEnvAmt", "Voice filter", "Env amount", lin(-40, 40, 7), 0, {"vcfType": 1, "vcfCut": 450}, True),
    ("vcfVel", "Voice filter", "Velocity", lin(0, 100), 100, {"vcfType": 1, "vcfCut": 450, "vcfEnvAmt": 30}, False),
    # The oscillator
    ("oscFm", "Oscillator", "FM", lin(0, 100), 0, {}, False),
    ("oscRatio", "Oscillator", "Ratio (with FM 30)", [0, 1, 2, 3, 4, 5, 7, 9, 12], 1, {"oscFm": 30}, False),
    ("oscRing", "Oscillator", "Ring", lin(0, 100), 0, {"oscRatio": 2}, False),
    ("oscSync", "Oscillator", "Sync", lin(100, 800), 100, {}, False),
    ("oscBend", "Oscillator", "Warp", lin(-100, 100, 7), 0, {}, True),
    ("oscBendAt", "Oscillator", "Warp at", lin(0, 100), 25, {"oscBend": 60}, False),
    ("oscSub", "Oscillator", "Sub", lin(0, 100), 0, {}, False),
    ("oscUnison", "Oscillator", "Unison", [1, 2, 3, 5, 7], 1, {}, False),
    ("oscSpread", "Oscillator", "Spread", lin(0, 50), 12, {"oscUnison": 5}, False),
    # Shaping
    ("shpDrive", "Shaping", "Drive", lin(0, 100), 0, {}, False),
    ("shpFold", "Shaping", "Fold", lin(0, 100), 0, {}, False),
    ("shpBits", "Shaping", "Crush (bits)", [0, 8, 6, 4, 3, 2, 1], 0, {}, False),
    ("shpRate", "Shaping", "Rate", [0, 11025, 8000, 4000, 2000, 1000, 500], 0, {}, False),
    ("shpOS", "Shaping", "Oversampling (Drive 70)", [2, 4], 2, {"shpDrive": 70}, False),
    # The Plane, the first module of Space & Memory
    ("planeTwist", "Plane", "Twist", lin(-100, 100, 7), 0, {}, True),
    ("rotate", "Plane", "Turn", lin(-50, 50, 7), 0, {}, True),
    ("planeSnap", "Plane", "Snap", [0, 5, 6], 0, {}, False),
    ("planeMirror", "Plane", "Mirror", [0, 1, 2, 3], 0, {}, False),
    ("planeLimit", "Plane", "Limit", [0, 1, 2], 0, {}, False),
    ("planeRadius", "Plane", "Radius (Limit radial)", lin(2, 100), 40, {"planeLimit": 1}, False),
    ("planeScaleX", "Plane", "Scale X", lin(0, 200, 7), 100, {}, True),
    ("planeScaleY", "Plane", "Scale Y", lin(0, 200, 7), 100, {}, True),
    ("planeShear", "Plane", "Shear", lin(-100, 100, 7), 0, {}, True),
    ("planeOS", "Plane", "Oversampling (Twist 50)", [1, 2, 4], 2, {"planeTwist": 50}, False),
    # The EQ, switched on
    ("eqLow", "EQ", "Low", lin(-160, 120, 8), 0, {"eqOn": True}, True),
    ("eqMid", "EQ", "Mid", lin(-160, 120, 8), 0, {"eqOn": True}, True),
    ("eqHigh", "EQ", "High", lin(-160, 120, 8), 0, {"eqOn": True}, True),
    ("eqMidFreq", "EQ", "Mid freq (Mid +8)", lin(0, 1000), 567, {"eqOn": True, "eqMid": 80}, False),
    ("eqCutHighFreq", "EQ", "High cut", lin(0, 1000), 985, {"eqOn": True, "eqCutHighOn": True}, False),
    ("eqCutLowFreq", "EQ", "Low cut", lin(0, 1000), 59, {"eqOn": True, "eqCutLowOn": True}, False),
    # Phaser, chorus, delay, reverb: each switched on at its start where its knobs need it
    ("phaserMix", "Phaser", "Mix", lin(0, 100), 0, {}, False),
    ("phaserRate", "Phaser", "Rate", [5, 15, 30, 80, 200, 500], 30, {"phaserMix": 50}, False),
    ("phaserDepth", "Phaser", "Depth", lin(0, 100), 70, {"phaserMix": 50}, False),
    ("phaserFeedback", "Phaser", "Feedback", lin(0, 75), 30, {"phaserMix": 50}, False),
    ("chorusMix", "Chorus", "Mix", lin(0, 100), 0, {}, False),
    ("chorusRate", "Chorus", "Rate", [5, 20, 60, 150, 300, 500], 60, {"chorusMix": 50}, False),
    ("chorusDepth", "Chorus", "Depth", lin(0, 100), 30, {"chorusMix": 50}, False),
    ("chorusTime", "Chorus", "Time", lin(10, 300), 120, {"chorusMix": 50}, False),
    ("chorusFeedback", "Chorus", "Feedback", lin(0, 90), 0, {"chorusMix": 50}, False),
    ("delayMix", "Delay", "Mix", lin(0, 100), 0, {}, False),
    ("delayMs", "Delay", "Time", [10, 40, 120, 375, 900, 2000], 375, {"delayMix": 35}, False),
    ("delayFeedback", "Delay", "Feedback", lin(0, 90), 35, {"delayMix": 35}, False),
    ("delayTone", "Delay", "Tone", lin(0, 100), 100, {"delayMix": 35}, False),
    ("delayLowCut", "Delay", "Low cut", lin(0, 100), 0, {"delayMix": 35}, False),
    ("delayWidth", "Delay", "Width", lin(0, 200), 100, {"delayMix": 35}, False),
    ("delayWow", "Delay", "Wow", lin(0, 100), 0, {"delayMix": 35}, False),
    ("delayPingPong", "Delay", "Ping-pong", [False, True], False, {"delayMix": 35}, False),
    ("reverbMix", "Reverb", "Mix", lin(0, 100), 0, {}, False),
    ("reverbSize", "Reverb", "Size", lin(0, 100), 40, {"reverbMix": 30}, False),
    ("reverbTone", "Reverb", "Tone", lin(0, 100), 60, {"reverbMix": 30}, False),
    ("reverbPre", "Reverb", "Pre-delay", lin(0, 100), 10, {"reverbMix": 30}, False),
    ("reverbSpread", "Reverb", "Spread", lin(0, 100), 0, {"reverbMix": 30}, False),
    ("fxOrder", "Rack", "Order (all three on)", ["pcd", "pdc", "cpd", "cdp", "dpc", "dcp"], "pcd",
     {"phaserMix": 50, "chorusMix": 50, "delayMix": 35}, False),
    # The Picture and Scan: the loop
    ("oscScan", "Picture", "Scan", lin(0, 100), 0, {}, False),
    ("scanSoft", "Picture", "Softness (Scan 60)", lin(0, 60), 30, {"oscScan": 60}, False),
    ("scanStrike", "Picture", "Strike (Scan 60)", lin(0, 100), 50, {"oscScan": 60}, False),
    ("pictureAmount", "Picture", "Amount", lin(0, 100), 0, {}, False),
    ("pictureSwell", "Picture", "Swell (Amount 80)", [False, True], False, {"pictureAmount": 80}, False),
    ("pictureResponds", "Picture", "Responds to (Amount 80)", ["change", "level", "both"], "change", {"pictureAmount": 80}, False),
    ("pictureRise", "Picture", "Rise (Amount 80)", [5, 20, 80, 300, 900, 2000], 80, {"pictureAmount": 80, "pictureFeel": "custom"}, False),
    ("pictureFall", "Picture", "Fall (Amount 80)", [20, 100, 400, 800, 3000, 8000], 800, {"pictureAmount": 80, "pictureFeel": "custom"}, False),
    ("persistence", "Picture", "Persistence (Scan 60, Amount 80)", ["0", "0.3", "0.12", "0.04", "-1"], "0.3",
     {"oscScan": 60, "pictureAmount": 80}, False),
    ("display", "Picture", "Display Y-T / X-Y (Scan 60)", ["xy", "yt"], "xy", {"oscScan": 60}, False),
    ("screenDraws", "Picture", "Trace / Paint (Scan 60, Amount 80)", ["trace", "paint"], "trace", {"oscScan": 60, "pictureAmount": 80}, False),
    ("soundWidth", "Picture", "Width (Draw width on)", lin(0, 100), 50, {"widthDrawn": True}, False),
    # The null: no control at all, the key landing a few milliseconds later. Nothing an
    # ear could call a change, so whatever it moves from a base is that base's own
    # chaos - the loop magnifies where in its state a note lands - and the floor an
    # effect has to clear before it counts as one (analyse.py).
    ("_land", "Null", "The key a moment later (ms)", [0, 1, 3, 7, 13, 20], 0, {}, False),
]

# Left out, and why: see LEFT_OUT, which the page prints.
LEFT_OUT = [
    ("width, morph, table, bars, cycle", "act only on their own shape (Pulse, Morph, Wavetable, Drawbars, Drawn), which none of the four bases plays; the shape menu itself is measured as points from the sine (SHAPES)"),
    ("interval", "the second note of Dyad; the bases play Poly"),
    ("freq", "the pitch with no key down; every render plays a key"),
    ("envShape, vcfShape, menvShape and their points", "the drawn envelopes: their knobs (Attack, Decay, Sustain, Release, Delay, Hold) are measured, and a hand-drawn point has no range to sweep"),
    ("vcfAtk, vcfDec, vcfSus, vcfRel, vcfDelay, vcfHold", "the filter envelope's times: the filter's Env amount is measured; its times shape it as the amp's do, which the amp envelope's sweeps cover"),
    ("oscSubOct, oscSubShape", "two choices each on the Sub, measured"),
    ("eqLowFreq, eqHighFreq, eqMidWidth, eqCutLowQ, eqCutHighQ", "where the measured bands sit; Mid freq and both cuts stand for them"),
    ("LFO 1 and 2, the Envelope card, the Photocell, the routings (l0*, l1*, menv*, photo*, mod, modB, modSilent)", "modulation sources: each moves a destination, and every destination they can reach is a control measured here"),
    ("midiMode, midiHold, midiRetrig, bendRange, wheelTo, pressureTo, arp*, quant, keyScale, keyRoot, bpm, score*", "how notes are played, not what they sound like; a source of percussion (the arpeggiator) is a pattern, not a timbre"),
    ("layers, split*, layerPair, pictureMoves*, scanReads*", "which hand plays and reads what; the presets that use them are points on the map"),
    ("morphA, morphB, morphPos", "the morph crossfades two setups, so its path is the two ends' straight line"),
    ("bPlane and every b* field", "the upper hand's twin of a measured control"),
    ("paintPersistence", "Paint's own half-life; Trace / Paint is measured"),
    ("zoom, timebase, level, trig, edge, position, holdoff, trigMode, span, c0*, c1*, midSide, acHz, octaves, lag*, fOn, fType, fCut, fRes, fSee, fHear, mSee, xy0, xy1, p*, cursors, beam*, bInk, trace, graticule, widthDrawn, the Trail, Which hands, the inks", "only the look or the scope's own measuring; Scan reads the trace's grid, and these change how it is shown, not what is drawn into it (display, persistence and Trace / Paint, which do, are measured)"),
    ("photoOn, photoU, photoV", "the Photocell is a modulation source: on its own it moves nothing"),
    ("inputMode, inputDepth", "the live input into the generator; nothing is played in"),
    ("Output", "how loud you hear, the same to the bit otherwise, and no setup's"),
]
SHAPES = ["sine", "harmonic", "triangle", "square", "pulse", "ramp", "drawbars", "morph", "wavetable", "noise", "pink", "brown", "stepped"]

# ---------------------------------------------------------------- the scripts

A3 = 57
UP = 5             # the second held note, a fourth up, for the aliasing measure
RATIO = 2 ** (UP / 12)
PHRASE = [(57, 100), (60, 70), (64, 115), (62, 60), (69, 110), (64, 85)]
HELD_ON, HELD_OFF, HELD_END = 0.2, 3.2, 4.2
STEP = 0.32

def notes_of(setup):
    """The held note: A3, or in a split A2 under A4 (each hand one, both on 110 Hz's harmonics)."""
    return ([45, 69], 110.0) if setup.get("layers") == "split" else ([A3], 220.0)

def held_script(code, patch, notes, up=0):
    notes = [n + up for n in notes]
    patch = dict(patch); land = patch.pop("_land", 0) / 1000
    return [["make", None, code, patch], ["record", "heard", None], ["to", HELD_ON + land]] \
        + [["midi", 0x90, n, 100] for n in notes] + [["to", HELD_OFF]] + [["midi", 0x80, n, 0] for n in notes] \
        + [["to", HELD_END], ["record", "heard"]]

def phrase_script(code, patch, split):
    patch = dict(patch); land = patch.pop("_land", 0) / 1000
    lines = [["make", 48000, code, patch], ["record", "heard", None], ["to", 0.2 + land]]
    t = 0.2
    for i, (n, v) in enumerate(PHRASE):
        n = n + (12 if split and i % 2 else -12 if split else 0)
        lines += [["midi", 0x90, n, v], ["to", t + STEP * (0.85 if i < len(PHRASE) - 1 else 2.5)], ["midi", 0x80, n, 0]]
        t += STEP
        if i < len(PHRASE) - 1: lines += [["to", t]]
    return lines + [["to", t + STEP * 2.5 + 1.0], ["record", "heard"]]

def run(job):
    """One render: the script with its rate and file filled in; the heard pair as a float array."""
    renderer, lines, rate = job
    tag = hashlib.sha1((renderer + json.dumps(lines) + str(rate)).encode()).hexdigest()[:16]
    script, audio = os.path.join(BUILD, "s-%s.txt" % tag), os.path.join(BUILD, "h-%s.f32" % tag)
    out = []
    for l in lines:
        l = list(l)
        if l[0] == "make": l[1] = rate
        if l[0] == "record" and len(l) == 3: l[2] = audio
        out.append(l)
    with open(script, "w") as f: f.write("\n".join(json.dumps(l) for l in out) + "\n")
    subprocess.run([RENDER[renderer], script], check=True, capture_output=True)
    x = np.fromfile(audio, dtype=np.float32).reshape(-1, 2).astype(np.float64)
    os.remove(script); os.remove(audio)
    return x

# ---------------------------------------------------------------- the measures

FEATURES = [
    # key, name, what it reads
    ("bright", "Brightness", "the spectral centroid of the held note's sustain, in octaves over the note"),
    ("noise", "Noisiness", "the share of the sustain's energy in the floor: bins that are neither a harmonic's nor a sharp partial's, each counted once, both notes averaged, in dB"),
    ("flat", "Flatness", "spectral flatness of 4096-sample frames, 50 Hz to 16 kHz, in dB (a sine about -100, white noise about -2)"),
    ("alias", "Grit (aliasing)", "the share of energy in sharp partials that are not the note's harmonics, do not follow the note (held a fourth higher, they are not at the same multiple of it), and sit in the gaps between harmonics, 0.15 of the note or more from either: a bitcrusher's folded steps, a hold's images, in dB"),
    ("shimmer", "Shimmer", "the same partials that do not follow the note, but on a harmonic's skirt, within 0.15 of the note of it: a chorus's or a unison's sidebands, in dB"),
    ("inharm", "Inharmonicity", "the share in sharp partials that are not the note's harmonics and do follow it, at the same multiple a fourth higher (an FM bell's), in dB"),
    ("loud", "Loudness", "the sustain's RMS, in dB of full scale"),
    ("attack", "Attack", "from the key to 90 per cent of the note's loudest 5 ms, log10 of ms"),
    ("sustain", "Sustain", "the last 0.7 s held against the loudest moment, in dB (0 an organ, -30 a pluck)"),
    ("tail", "Tail", "0.1 to 0.6 s after the key comes up against the held sound, in dB"),
    ("width", "Stereo width", "the side's energy against the mid's over the sustain, in dB"),
    ("move", "Movement", "spectral flux of the sustain: the distance between fifth-octave spectra 43 ms apart, as honestytest reads movement"),
    ("wobble", "Wobble", "the spread of the sustain's loudness in 20 ms windows, in dB"),
    ("evenodd", "Even/odd", "harmonics 2 to 20: the even ones' energy against the odd ones', in dB"),
    ("artic", "Articulation", "in the phrase, how far each note's first 30 ms stand over the 30 ms before it, in dB, the median"),
]
KEYS = [k for k, _, _ in FEATURES]

def db(x, floor=1e-7): return float(10 * np.log10(max(x, floor)))

def spectra_1hz(mono, rate, t0, t1):
    """Power spectra at 1 Hz a bin, Hann windows a second long, half overlapped."""
    n = int(rate)
    w = np.hanning(n)
    out = []
    s = int(t0 * rate)
    while s + n <= int(t1 * rate):
        out.append(np.abs(np.fft.rfft(mono[s:s + n] * w)) ** 2)
        s += n // 2
    return out

def spectrum_1hz(mono, rate, t0, t1):
    """Their average."""
    ws = spectra_1hz(mono, rate, t0, t1)
    return np.mean(ws, axis=0) if ws else np.zeros(int(rate) // 2 + 1)

def partials(p, f0, top=20000):
    """The spectrum split by bins, each bin counted once: the note's harmonics (4 Hz either side
    of each), the sharp non-harmonic peaks (a local maximum 12 dB over the median within 60 Hz,
    and the two bins either side of it), and the floor, everything else. Peaks are returned
    with the energy of the bins they claim; a bin two peaks reach goes to the first."""
    f = np.arange(len(p))
    p = p[:top]; f = f[:top]
    use = f >= 20
    total = p[use].sum()
    harm = np.zeros(len(p), bool)
    for k in range(1, int(top / f0) + 1):
        c = int(round(k * f0)); harm[max(0, c - 4):c + 5] = True
    med = np.array([np.median(p[max(0, i - 60):i + 61]) for i in range(0, len(p), 20)])
    med = np.repeat(med, 20)[:len(p)]
    loc = (p > np.roll(p, 1)) & (p >= np.roll(p, -1)) & (p > 16 * med) & ~harm & use
    claimed = harm.copy()
    peaks = {}
    for i in np.nonzero(loc)[0]:
        lo, hi = max(0, i - 2), min(len(p), i + 3)
        free = ~claimed[lo:hi]
        peaks[int(i)] = float(p[lo:hi][free].sum())
        claimed[lo:hi] = True
    tonal = sum(peaks.values())
    floor = float(p[(~claimed) & use].sum())
    return total, float(p[harm & use].sum()), peaks, tonal, floor

def measure_held(x48, x44, f0, ratio=RATIO, land=0.0):
    """x48 the held A3, x44 the same held a fourth up (D4), both at 48 kHz."""
    out = {}
    m48 = x48.mean(axis=1); m44 = x44.mean(axis=1)
    s0, s1 = HELD_ON + 0.7, HELD_OFF
    # The spectra over the whole held note from just after the key, energy-weighted as an
    # average of power is: over the sustain alone a pluck whose sustain is nought has
    # nothing left to read, and its "centroid" was the noise floor's (-8.9 octaves).
    w0 = HELD_ON + land + 0.05
    win48 = spectra_1hz(m48, 48000, w0, s1); win44 = spectra_1hz(m44, 48000, w0, s1)
    p48 = np.mean(win48, axis=0); p44 = np.mean(win44, axis=0)
    fr = np.arange(len(p48))
    band = (fr >= 20) & (fr <= 20000)
    out["bright"] = float(np.log2(max((fr[band] * p48[band]).sum() / max(p48[band].sum(), 1e-30), 1) / f0))
    tot48, h48, pk48, ton48, nh48 = partials(p48, f0)
    tot44, h44, pk44, ton44, nh44 = partials(p44, f0 * ratio)
    # A partial the sound is made of scales with the note; one folded back by a
    # sample rate (the host's or Rate's own) or an image of a hold does not. Each
    # note's peaks on the axis of its own harmonics, f / f0, matched within 0.012.
    def split(a, fa, b, fb):
        rb = np.array(sorted(i / fb for i in b)) if b else np.array([1e9])
        stay, moved = 0.0, {}
        for i, e in a.items():
            r = i / fa
            j = np.searchsorted(rb, r)
            near = min(abs(rb[min(j, len(rb) - 1)] - r), abs(rb[max(j - 1, 0)] - r))
            if near <= 0.012: stay += e
            else: moved[i] = e
        return stay, moved
    st48, mv48 = split(pk48, f0, pk44, f0 * ratio); st44, mv44 = split(pk44, f0 * ratio, pk48, f0)
    # What does not follow the note, by where it sits: in the gap between two harmonics,
    # 0.15 of the note or more from either (grit: a crusher's folding, a hold's images, which
    # land anywhere), or on a harmonic's skirt (shimmer: a chorus's or a unison's sidebands,
    # which a modulation puts round the partial it moves). Validated in --validate.
    def gap(moved, f):
        g = sum(e for i, e in moved.items() if abs(i / f - round(i / f)) >= 0.15)
        return g, sum(moved.values()) - g
    grit48, wan48 = gap(mv48, f0); grit44, wan44 = gap(mv44, f0 * ratio)
    tot = max(tot48, 1e-30); tot_ = max(tot44, 1e-30)
    out["alias"] = db((grit48 / tot + grit44 / tot_) / 2, 1e-6)
    out["shimmer"] = db((wan48 / tot + wan44 / tot_) / 2, 1e-6)
    out["tonal"] = db((ton48 / tot + ton44 / tot_) / 2, 1e-6)
    out["inharm"] = db((st48 / tot + st44 / tot_) / 2, 1e-6)
    out["noise"] = db((nh48 / tot + nh44 / tot_) / 2, 1e-6)
    # flatness, per 4096 frame
    n = 4096; fl = []
    s, e = int(s0 * 48000), int(s1 * 48000)
    ff = np.fft.rfftfreq(n, 1 / 48000); sel = (ff >= 50) & (ff <= 16000)
    for a in range(s, e - n, n):
        q = np.abs(np.fft.rfft(m48[a:a + n] * np.hanning(n))) ** 2
        q = q[sel] + 1e-12 * max(q[sel].mean(), 1e-30) + 1e-30
        fl.append(10 * np.log10(np.exp(np.mean(np.log(q))) / q.mean()))
    out["flat"] = float(np.mean(fl)) if fl else -100.0
    sus = m48[s:e]
    out["loud"] = db(np.mean(sus ** 2), 1e-12)
    # envelope at 5 ms
    hop = 240
    env = np.sqrt(np.convolve(m48 ** 2, np.ones(hop) / hop, "same")[::hop])
    on, off = int((HELD_ON + land) * 48000 / hop), int(HELD_OFF * 48000 / hop)
    held = env[on:off]
    peak = held.max() if held.size else 0
    if peak > 1e-6:
        out["attack"] = float(np.log10(max(1.0, np.argmax(held >= 0.9 * peak) * hop / 48)))
        out["sustain"] = db(np.mean(env[off - int(0.7 * 200):off] ** 2) / peak ** 2, 1e-6)
    else:
        out["attack"], out["sustain"] = 0.0, -60.0
    heldp = np.mean(sus ** 2)
    a, b = int((HELD_OFF + 0.1) * 48000), int((HELD_OFF + 0.6) * 48000)
    out["tail"] = db(np.mean(m48[a:b] ** 2) / max(heldp, 1e-20), 1e-6)
    side = (x48[:, 0] - x48[:, 1]) / 2
    out["width"] = db(np.mean(side[s:e] ** 2) / max(heldp, 1e-20), 1e-6)
    # movement: fifth-octave band spectra of 4096 frames 2048 apart
    edges = 40 * 2 ** (np.arange(49) / 5)
    bidx = np.clip(np.searchsorted(edges, ff) - 1, -1, 47)
    prev, moves = None, []
    for a in range(s, e - n, 2048):
        if np.mean(m48[a:a + n] ** 2) < 1e-9: prev = None; continue  # silence has no spectrum to move
        q = np.abs(np.fft.rfft(m48[a:a + n] * np.hanning(n))) ** 2
        bands = np.bincount(bidx[bidx >= 0], weights=q[bidx >= 0], minlength=48)
        bands = np.sqrt(bands / max(bands.sum(), 1e-30))
        if prev is not None: moves.append(float(np.sqrt(((bands - prev) ** 2).sum())))
        prev = bands
    out["move"] = float(np.mean(moves)) if moves else 0.0
    e20 = sus[: len(sus) // 960 * 960].reshape(-1, 960)
    lv = 10 * np.log10(np.maximum((e20 ** 2).mean(axis=1), 1e-12))
    out["wobble"] = float(np.std(lv))
    hk = [p48[max(0, int(round(k * f0)) - 4):int(round(k * f0)) + 5].sum() for k in range(1, 21)]
    # Only where harmonics 2 to 20 carry at least a hundredth of the note: on a sine the ratio
    # is of two near-noughts (Sync read +181 dB from it). Nought - neither - otherwise, and
    # held within 30 dB either way.
    if sum(hk[1:]) >= 0.01 * max(tot48, 1e-30):
        out["evenodd"] = float(np.clip(db(sum(hk[1::2]) / max(sum(hk[2::2]), 1e-30), 1e-9), -30, 30))
    else:
        out["evenodd"] = 0.0
    out["profile"] = [round(db(h / max(tot48, 1e-30), 1e-9), 1) for h in hk]
    return out

def measure_phrase(x):
    m = x.mean(axis=1)
    w = int(0.03 * 48000)
    got = []
    for i in range(len(PHRASE)):
        a = int((0.2 + i * STEP) * 48000)
        before = np.mean(m[a - w:a] ** 2) if i else 1e-10
        after = np.mean(m[a:a + w] ** 2)
        got.append(10 * np.log10(max(after, 1e-12) / max(before, 1e-12)))
    return {"artic": float(np.clip(np.median(got[1:]), -10, 40))}

def finite(d):
    return {k: (v if not isinstance(v, float) or np.isfinite(v) else 0.0) for k, v in d.items()}

# ---------------------------------------------------------------- the jobs

def measured(job):
    """A whole measurement: the held note at both rates and the phrase."""
    renderer, code, patch, split, f0, notes = job
    held = held_script(code, patch, notes)
    x48 = run((renderer, held, 48000))
    x44 = run((renderer, held_script(code, patch, notes, UP), 48000))
    xp = run((renderer, phrase_script(code, patch, split), 48000))
    f = measure_held(x48, x44, f0, land=patch.get("_land", 0) / 1000)
    f.update(measure_phrase(xp))
    f["peak"] = float(np.abs(x48).max())
    f["nonfinite"] = int((~np.isfinite(x48)).sum())
    return finite(f)

def key_of(job): return hashlib.sha1(json.dumps(job, sort_keys=True).encode()).hexdigest()

def jobs():
    """Every render: (label dict, job)."""
    out = []
    for b, (bname, setup) in BASES.items():
        code = code_of(setup)
        notes, f0 = notes_of(setup)
        out.append(({"kind": "base", "base": b}, ("core", code, {}, False, f0, notes)))
        for cid, group, name, places, rest, needs, two in CONTROLS:
            # the path starts where the base has the control, else at its rest
            r = setup.get(cid, DEFAULTS[cid] if rest is None else rest)
            for v in sorted(set(map(json.dumps, places + [r]))):
                v = json.loads(v)
                out.append(({"kind": "sweep", "base": b, "control": cid, "value": v, "rest": r},
                            ("core", code, dict(needs, **{cid: v}), False, f0, notes)))
        # Scan's sweep under each smooth prototype
        for variant in SMOOTH:
            for v in lin(0, 100):
                out.append(({"kind": "smooth", "variant": variant, "base": b, "control": "oscScan", "value": v, "rest": 0},
                            (variant, code, {"oscScan": v}, False, f0, notes)))
        if b == "sine":
            for sh in SHAPES:
                out.append(({"kind": "shape", "base": b, "value": sh}, ("core", code, {"shape": sh}, False, f0, notes)))
    for section, name, setup in PRESETS:
        notes, f0 = notes_of(setup)
        out.append(({"kind": "preset", "section": section, "name": name},
                    ("core", code_of(setup), {}, setup.get("layers") == "split", f0, notes)))
    return out

def defaults():
    s = open(os.path.join(CORE, "include", "scope", "schema.h")).read()
    d = json.loads("".join(re.findall(r'R"fields\((.*?)\)fields"', s, re.S)))
    return {k: v[0] for k, v in d.items()}
DEFAULTS = defaults()

# ---------------------------------------------------------------- validation

def validate():
    """The aliasing measure on sounds whose answer is known, at both rates, written as numpy here."""
    def saw_bl(rate, f0, t):  # band-limited: harmonics to the Nyquist
        x = np.zeros_like(t)
        for k in range(1, int(rate / 2 / f0) + 1): x += np.sin(2 * np.pi * k * f0 * t) / k
        return 0.5 * x
    def crush(x, rate, bits, hz):
        q = 2 ** (bits - 1); y = np.round(x * q) / q
        held = np.floor(np.arange(len(y)) * hz / rate).astype(int)
        first = np.searchsorted(held, held)
        return y[first]
    def tanh_os(rate, f0, t):  # a sine through tanh at 16x, filtered back down: clean
        tt = np.arange(len(t) * 16) / (rate * 16)
        y = np.tanh(3 * np.sin(2 * np.pi * f0 * tt))
        Y = np.fft.rfft(y); Y[int(len(Y) / 16 * 0.9):] = 0
        return 0.5 * np.fft.irfft(Y, len(tt))[::16]
    def fm_bell(rate, f0, t): return 0.5 * np.sin(2 * np.pi * f0 * t + 3 * np.sin(2 * np.pi * f0 * 1.4 * t))
    def white(rate, f0, t): return 0.3 * np.random.RandomState(1).randn(len(t))
    cases = [("clean band-limited saw", saw_bl), ("bitcrusher: the saw at 4 bits, held at 4 kHz", lambda r, f, t: crush(saw_bl(r, f, t), r, 4, 4000)),
             ("bitcrusher: 4 bits only", lambda r, f, t: crush(saw_bl(r, f, t), r, 4, r)),
             ("sample hold only, 4 kHz", lambda r, f, t: crush(saw_bl(r, f, t), r, 24, 4000)),
             ("a saw whose level steps sixty times a second", lambda r, f, t: saw_bl(r, f, t) * (0.75 + 0.25 * np.random.RandomState(2).rand(int(t[-1] * 60) + 2)[(t * 60).astype(int)])),
             ("a saw through a chorus (a 0.6 Hz, 3 ms sweep)", lambda r, f, t: 0.5 * saw_bl(r, f, t) + 0.5 * np.interp(t - 0.006 - 0.003 * np.sin(2 * np.pi * 0.6 * t), t, saw_bl(r, f, t))),
             ("bitcrusher: a sine at 3 bits", lambda r, f, t: crush(0.9 * np.sin(2 * np.pi * f * t), r, 3, r)),
             ("tanh drive, oversampled", tanh_os),
             ("tanh drive, not oversampled", lambda r, f, t: 0.5 * np.tanh(6 * saw_bl(r, f, t))), ("FM bell, ratio 1.4", fm_bell), ("white noise", white)]
    rows = []
    for name, fn in cases:
        xs = {}
        for f0 in (220.0, 220.0 * RATIO):
            t = np.arange(int(HELD_END * 48000)) / 48000
            y = fn(48000, f0, t)
            y[: int(HELD_ON * 48000)] = 0
            xs[f0] = np.stack([y, y], 1)
        f = measure_held(xs[220.0], xs[220.0 * RATIO], 220.0)
        rows.append({"name": name, **{k: round(f[k], 2) for k in ("bright", "alias", "shimmer", "inharm", "noise", "flat")}})
        print("%-48s grit %6.1f  shimmer %6.1f  inharm %6.1f  noise %6.1f  flat %6.1f  bright %.2f" % (name, f["alias"], f["shimmer"], f["inharm"], f["noise"], f["flat"], f["bright"]))
    return rows

if __name__ == "__main__":
    if "--validate" in sys.argv:
        validate(); sys.exit(0)
    cache = {} if "--fresh" in sys.argv or not os.path.exists(CACHE) else json.load(open(CACHE))
    todo = jobs()
    need = [j for _, j in todo if key_of(j) not in cache]
    print("%d renders, %d to measure" % (len(todo), len(need)))
    with Pool(4) as pool:
        for i, (j, f) in enumerate(zip(need, pool.imap(measured, need, chunksize=2))):
            cache[key_of(j)] = f
            if i % 50 == 0:
                print(" ", i, flush=True); json.dump(cache, open(CACHE, "w"))
    json.dump(cache, open(CACHE, "w"))
    results = {"features": FEATURES, "controls": [list(c[:5]) + [c[5], c[6]] for c in CONTROLS], "left_out": LEFT_OUT,
               "bases": {k: v[0] for k, v in BASES.items()}, "base_setups": {k: v[1] for k, v in BASES.items()},
               "validation": validate(), "renders": []}
    for label, j in todo:
        results["renders"].append(dict(label, f={k: (round(v, 4) if isinstance(v, float) else v) for k, v in cache[key_of(j)].items()}))
    json.dump(results, open(os.path.join(HERE, "results.json"), "w"))
    print("results.json:", len(results["renders"]), "renders")
