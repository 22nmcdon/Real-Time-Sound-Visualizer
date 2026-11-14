"""The voices' budget, on the core: budgettest.py's numbers rows.

These were budgettest.py's on `?brain=js` until stage 5, step 3, batch 6 (14
Nov): the page's own `makeGeneratorCore` built in the browser, set by hand
(`core.set`, `core.set('voices', ...)`), its `core.budget` and its voices'
`cut` read back, and its blocks timed with `performance.now()` - the page's
JavaScript engine throughout. Here the core's own generator through
core/tests/tools/budget_cpp.cpp, which drives it the same way - a block of
any length, the voices laid on directly, the budget and each voice read back,
and a second of it timed natively - and the old library and the bank
restored into it by the core's own restoreSetup.

Before anything moved, the two governors were run side by side on the same
scripts (14 Nov): every row's case, budgettest's sweep of one to eight notes a
layer with everything on, the chords over releases, the caps, the 4 kHz drive
and the fade, and all 277 setups of the old library and the bank under a chord
of eight a layer and under a chord over five-second releases. The page's model
and the core's thinned the same voices in the same order at every load,
exactly: the same units to the last bit, the same copies, factor and held
notes let go, and the same voices cut, voice for voice. So the order and the
caps are the core's to hold now, and they are held here, each with its null.

What did not move cleanly is the model's fit. Its costs were fitted to the
page's JavaScript in milliseconds, and natively the core spends them
differently: the noise and the filter cost well under half of what the model
says (0.35 to 0.42 of the median), everything else 0.6 to 1.5. Both are on the
safe side - a feature costed dearer than it is gives up a copy early, one
costed cheaper is a glitch - so the check below holds the side that matters
(nothing cheaper in the model than on the machine, past 1.6 of the median)
and names the two it no longer holds on the other. Nothing was refitted: a
refit changes what the instrument gives up under load, which is the owner's
to hear (web/docs/budget-on-the-core.md). The site runs the core as
WebAssembly, whose relative costs were not measured; native is the nearest
the pieces can time.

The timing checks are the only ones in the pieces that read a clock. Each
case is the best of five seconds (the worst case of three), and the bounds are
wide (half of real time for a governed worst case that takes about a sixth);
a loaded machine still moves the ratios by a tenth or two, which is why the
page's run.py marked its twin of the relative-cost check as known to flake.
"""
import json, math, os, subprocess

import numpy as np

RATE = 44100
BH = (0.35875, 0.48829, 0.14128, 0.01168)
HERE = os.path.dirname(os.path.abspath(__file__))
LIBRARY = os.path.join(os.path.dirname(HERE), "scenarios", "library-p8f.json")

# Everything on: the case that measured 1.7 seconds a second, on the page, ungoverned.
ALL = {"shape": "drawbars", "unison": 7, "fmIndex": 2, "syncRatio": 1.5, "subLevel": 0.5, "drive": 0.5,
       "fold": 0.3, "vcfType": 1, "vcfEnv": 2, "vcfTrack": 1, "crushBits": 6, "shapeOS": 4}

CASES = {
    "saw": {"shape": "ramp"}, "sine": {"shape": "sine"}, "pulse": {"shape": "pulse"},
    "morph": {"shape": "morph", "morph": 1.5}, "drawbars": {"shape": "drawbars"},
    "wavetable": {"shape": "wavetable"}, "drawn": {"shape": "drawn"}, "pink": {"shape": "pink"},
    "saw x7": {"shape": "ramp", "unison": 7}, "morph x7": {"shape": "morph", "morph": 1.5, "unison": 7},
    "drawbars x7": {"shape": "drawbars", "unison": 7}, "pulse x7": {"shape": "pulse", "unison": 7},
    "saw x7 fm": {"shape": "ramp", "unison": 7, "fmIndex": 2},
    "saw x7 sync": {"shape": "ramp", "unison": 7, "syncRatio": 1.5},
    "saw x7 ring sub": {"shape": "ramp", "unison": 7, "ringMix": 0.5, "subLevel": 0.5},
    "drive 2x": {"shape": "ramp", "drive": 0.5}, "drive 4x": {"shape": "ramp", "drive": 0.5, "shapeOS": 4},
    "filter": {"shape": "ramp", "vcfType": 1, "vcfEnv": 2}, "plane 4x": {"shape": "ramp", "planeMirror": 3,
    "planeLimit": 1, "planeRadius": 0.3, "planeOS": 4},
    "everything": ALL,
}


def chord(base, hz=None, n=8, roles=None):
    """budgettest's chord: eight notes a minor third apart, the lowest drawn on
    X and the highest on Y, the rest inner - or the roles given."""
    out = []
    for k in range(8):
        f = hz * (1 + k / 8) if hz else 440 * 2 ** ((base + k * 3 - 69) / 12)
        role = roles[k] if roles else "x" if k == 0 else "y" if k == 7 else "u"
        out.append("%d/%r/1/%s" % (base + k * 3, f, role))
    return "+".join(out[:n])


def setall(cfg, layers=(0, 1)):
    return ["set %s %s %d" % (k, v, l) for l in layers for k, v in cfg.items()]


class Read:
    """budget_cpp's lines: each `budget` as a dict, each `pool` as voices, each `heard` as samples."""
    def __init__(self, text):
        self.budgets, self.pools, self.heard, self.times, self.words = [], [], [], [], {}
        for line in text.split("\n"):
            w = line.split()
            if not w: continue
            if w[0] == "budget":
                v = [float(x) for x in w[1:]]
                self.budgets.append({"units": v[0], "asked": [int(v[1]), int(v[2])], "unison": [int(v[3]), int(v[4])],
                                     "askedFactor": int(v[5]), "factor": int(v[6]), "silenced": int(v[7]),
                                     "voices": [int(v[8]), int(v[9])]})
            elif w[0] == "pool":
                self.pools.append([dict(zip(("layer", "note", "held", "cut"), map(int, x.split(":")))) for x in w[1:]])
            elif w[0] == "heard": self.heard.append(np.array([float(x) for x in w[1:]]))
            elif w[0] == "time": self.times.append(float(w[1]))
            else: self.words[w[0]] = w[1:]


def off_grid(x, f0, top=10000):
    """The loudest thing off the harmonics of f0 below `top`, in dB under the
    loudest thing of all: what drive aliases back to. As drivetest.py and
    budgettest.py measured it."""
    x = np.asarray(x, dtype=float)
    i = np.arange(len(x))
    w = (BH[0] - BH[1] * np.cos(2 * np.pi * i / len(x)) + BH[2] * np.cos(4 * np.pi * i / len(x))
         - BH[3] * np.cos(6 * np.pi * i / len(x)))
    spec = np.abs(np.fft.rfft(x * w))
    hz = np.arange(len(spec)) * RATE / len(x)
    grid = np.zeros(len(spec), dtype=bool)
    grid[:6] = True
    k = 1
    while k * f0 < RATE / 2:
        grid |= np.abs(hz - k * f0) < 4 * RATE / len(x)
        k += 1
    return 20 * math.log10(max(spec[~grid & (hz < top)].max(), 1e-15) / spec.max())


def thinned(b, layered=True):
    return b["unison"][0] < b["asked"][0] or (layered and b["unison"][1] < b["asked"][1]) \
        or b["factor"] < b["askedFactor"] or b["silenced"] > 0


def run(kit):
    check, null = kit.check, kit.null
    go = lambda lines: Read(kit.run("budget_cpp", "\n".join(lines)))

    # --- the worst case, governed ---
    # A chord let go into long releases, and a second chord over them: thirty-two voices asked for.
    worst = go(["gen 44100"] + setall(ALL) + ["set releaseMs 5000 0", "set releaseMs 5000 1",
               "voices 0 " + chord(36), "voices 1 " + chord(36), "run 4410",
               "voices 0 " + chord(60), "voices 1 " + chord(60), "run 4410", "budget", "time"])
    wb, wms = worst.budgets[0], worst.times[0]
    one = go(["gen 44100", "set shape sine", "voices 0 " + chord(48, n=1), "run 4410", "time"]).times[0]
    print("    one second of it natively: %.1f ms (one sine voice %.2f ms), the model's %.1f of 350; %s" % (wms, one, wb["units"], wb))
    # On ?brain=js, the page's JavaScript under half of real time; here the
    # core natively. The site runs it as WebAssembly, slower than this, which
    # the pieces do not time.
    check("sixteen held notes and sixteen releasing, everything on, run in under half of real time",
          wms < 500, "%.1f ms" % wms)
    null("the clock reads the work: the worst case costs more than ten single sine voices", wms > 10 * one,
         "%.1f against %.2f ms" % (wms, one))
    check("and the model says the budget holds", wb["units"] <= 350, str(wb["units"]))
    null("and the governor fills it: the same bound at half the budget goes red", not wb["units"] <= 175, str(wb["units"]))

    # --- the model against the machine ---
    def per_layer(cfg, k):
        b = go(["gen 44100"] + setall(cfg) + ["voices 0 " + chord(48, n=k), "voices 1 " + chord(48, n=k), "run 128", "budget"]).budgets[0]
        return b, not thinned(b)
    model, edges = {}, {}
    for name, cfg in CASES.items():
        # As many voices a layer as the model leaves whole, so what is timed is what was asked.
        per = 1
        for k in range(1, 9):
            if not per_layer(cfg, k)[1]: edges[name] = k; break
            per = k
        r = go(["gen 44100"] + setall(cfg) + ["voices 0 " + chord(48, n=per), "voices 1 " + chord(48, n=per), "run 4410", "budget", "time 5"])
        model[name] = {"per": per, "ms": r.times[0], "units": r.budgets[0]["units"], "whole": not thinned(r.budgets[0])}
    ratios = {k: v["ms"] / v["units"] for k, v in model.items()}
    mid = sorted(ratios.values())[len(ratios) // 2]
    for k, v in model.items():
        print("    %-16s %d a layer  %7.2f ms  model %6.1f   %.2f of the median" % (k, v["per"], v["ms"], v["units"], ratios[k] / mid))
    print("    a unit is %.3f ms of work a second, natively" % mid)
    check("every case was measured as asked, the governor leaving it whole", all(v["whole"] for v in model.values()),
          str([k for k, v in model.items() if not v["whole"]]))
    # Its null: a voice more than the probe kept, where it stopped short of
    # eight, is thinned - so the probe found the edge rather than a case that
    # never thins.
    over = {k: per_layer(CASES[k], e)[1] for k, e in edges.items()}
    null("a voice a layer past where the probe stopped is thinned", len(over) >= 3 and not any(over.values()),
         "%d cases stopped short of eight: %s" % (len(over), sorted(over)))
    # On ?brain=js both sides, from half to 1.6 times the median, on the
    # page's JavaScript milliseconds. Natively the noise and the filter read
    # 0.35 to 0.42, costed dearer than they are: the safe side, which only
    # gives up a copy early. The side that glitches is held; the other is
    # named and recorded, not refitted (web/docs/budget-on-the-core.md).
    cheap = {k: round(r / mid, 2) for k, r in ratios.items() if r / mid > 1.6}
    dear = {k: round(r / mid, 2) for k, r in ratios.items() if r / mid < 0.5}
    print("    costed dearer than the core spends, under half the median: %s" % dear)
    check("no feature is costed cheaper than the core spends on it, past 1.6 times the median", cheap == {}, str(cheap))
    wrong = model["morph"]["ms"] / model["saw"]["units"] / mid
    null("the same rule goes red on a model that costs the morph as a saw", wrong > 1.6, "%.2f of the median" % wrong)

    # --- what is given up, and in what order ---
    order = []
    for k in range(1, 9):
        r = go(["gen 44100"] + setall(ALL) + ["voices 0 " + chord(48, n=k), "voices 1 " + chord(60, n=k), "run 128", "budget", "pool"])
        order.append(dict(r.budgets[0], k=k, pool=r.pools[0]))
    for o in order:
        print("    %d a layer: %dx, unison %s, %d held let go" % (o["k"], o["factor"], o["unison"], o["silenced"]))
    check("one note a layer, everything on, gives up nothing",
          order[0]["factor"] == 4 and order[0]["unison"] == [7, 7] and order[0]["silenced"] == 0, str(order[0]))
    null("and two a layer do give something up", thinned(order[1]), str(order[1]))
    check("unison is only thinned once the four times has gone",
          all(o["factor"] == 2 for o in order if o["unison"] != [7, 7]), str([(o["k"], o["factor"], o["unison"]) for o in order]))
    null("the same rule goes red on the sweep read with the four times kept where unison thinned",
         not all(4 == 2 for o in order if o["unison"] != [7, 7]))
    check("a held note is only let go once unison is down to one on both layers",
          all(o["unison"] == [1, 1] for o in order if o["silenced"] > 0), str([(o["k"], o["unison"], o["silenced"]) for o in order]))
    null("the same rule goes red on the sweep read with the copies as asked where notes were let go",
         not all(o["asked"] == [1, 1] for o in order if o["silenced"] > 0))
    # The oldest of a rank goes first. The voices are born in the order they
    # are laid on, A's chord and then B's, which is the order budget_cpp
    # lists them in, so the inner voices let go are the first of the inner
    # voices listed and none kept comes before one let go.
    full = order[-1]["pool"]
    inner8 = [v["cut"] for v in full if not ((v["layer"] == 0 and v["note"] in (48, 69)) or (v["layer"] == 1 and v["note"] in (60, 81)))]
    first = lambda cuts: 0 < sum(cuts) < len(cuts) and cuts == sorted(cuts, reverse=True)
    check("of the inner notes, the oldest are let go first", first(inner8), str(inner8))
    null("the same rule on the newest first goes red", not first(inner8[::-1]))
    check("each stage is reached somewhere between one note a layer and eight",
          any(o["factor"] == 2 for o in order) and any(o["unison"] != [7, 7] for o in order)
          and any(o["silenced"] > 0 for o in order), str(order[-1]))

    # An outline note only once every inner one has gone. On ?brain=js this
    # was "a drawn note only once every undrawn one has gone", read as a voice
    # with both gains at nought - which no voice has had since P4 drew the
    # inner voices too, so it held of nothing (all() over no undrawn voice).
    # Here the governor's own rule, inner before outline, on a chord with
    # more outline voices than budgettest's had, so that some outline does go.
    roles = ["x", "y", "x", "u", "y", "x", "u", "y"]
    inner = {(0, 48 + 3 * k) for k in range(8) if roles[k] == "u"} | {(1, 60 + 3 * k) for k in range(8) if roles[k] == "u"}
    r = go(["gen 44100"] + setall(ALL) + ["voices 0 " + chord(48, roles=roles), "voices 1 " + chord(60, roles=roles), "run 128", "pool"])
    pool = r.pools[0]
    outline_cut = [v for v in pool if v["cut"] and (v["layer"], v["note"]) not in inner]
    inner_left = [v for v in pool if not v["cut"] and (v["layer"], v["note"]) in inner]
    print("    with four inner notes in sixteen: %d outline let go, %d inner left" % (len(outline_cut), len(inner_left)))
    check("and an outline note only once every inner one has gone", outline_cut != [] and inner_left == [],
          "%d outline cut, %d inner left" % (len(outline_cut), len(inner_left)))
    null("the same rule with inner and outline swapped goes red",
         not ([v for v in pool if v["cut"] and (v["layer"], v["note"]) in inner] != [] and [v for v in pool if not v["cut"] and (v["layer"], v["note"]) not in inner] == []))

    # Two chords over releases: one layer without the shaper, where letting
    # some releases go is enough, and both with everything, where every
    # release goes and held notes after them.
    tails = []
    for both in (False, True):
        cfg = dict(ALL) if both else dict(ALL, drive=0, fold=0)
        r = go(["gen 44100"] + setall(cfg) + ["set releaseMs 5000", "voices 0 " + chord(36), "run 2205", "voices 0 " + chord(60)]
               + (["voices 1 " + chord(48)] if both else []) + ["run 64", "pool", "budget"])
        v = r.pools[0]
        tails.append({"released": sum(1 for x in v if not x["held"]), "releasedCut": sum(1 for x in v if not x["held"] and x["cut"]),
                      "heldCut": sum(1 for x in v if x["held"] and x["cut"]), "silenced": r.budgets[0]["silenced"]})
    print("    a chord over the releases of the last, on one layer and on two: %s" % tails)
    check("releases in flight go first: with some let go, no held note is",
          tails[0]["released"] == 8 and 0 < tails[0]["releasedCut"] < 8 and tails[0]["heldCut"] == 0, str(tails[0]))
    check("and a held note goes only once every release has",
          tails[1]["releasedCut"] == tails[1]["released"] == 8 and tails[1]["heldCut"] > 0, str(tails[1]))
    # What the readout calls "held notes let go" is the budget's count, so
    # releases cut must not be in it: a player told a held note went when
    # only tails had would go looking for a fault.
    check("and the budget counts only held notes as let go, not the releases it cut",
          tails[0]["silenced"] == 0 and tails[1]["silenced"] == tails[1]["heldCut"], str(tails))
    null("a count of every voice cut would say so on the first run", tails[0]["releasedCut"] > 0)
    null("the first rule goes red on the second run, where held notes do go",
         not (tails[1]["released"] == 8 and 0 < tails[1]["releasedCut"] < 8 and tails[1]["heldCut"] == 0))

    # Given up means given up, not only reported: a hard drive on a 4 kHz
    # note, as a chord of voices all on it and all in step. Two keep the four
    # times and alias at drivetest's -46 dB; twelve are over the budget and
    # have to be at twice, -30. A core that reported twice and ran four would
    # read -46 both times.
    drive = {}
    for count in (2, 12):
        v = "+".join("%d/4000/1/u" % (40 + k) for k in range(count))
        r = go(["gen 44100", "set shape sine", "set drive 0.8", "set shapeOS 4", "set amp 0.05", "voices 0 " + v, "run 4410", "heard 44100", "budget"])
        drive[count] = (off_grid(r.heard[0], 4000), r.budgets[0])
    few, many = drive[2][0], drive[12][0]
    print("    two driven voices at 4 kHz: %dx, %.1f dB; twelve: %dx, %.1f dB" % (drive[2][1]["factor"], few, drive[12][1]["factor"], many))
    check("two voices keep the four times and alias as it does, under -44 dB", drive[2][1]["factor"] == 4 and few < -44, "%.1f dB" % few)
    check("twelve are held to twice, and alias as twice does - the governor's choice is the one that runs",
          drive[12][1]["factor"] == 2 and drive[12][1]["silenced"] == 0 and -36 < many < -26, "%.1f dB" % many)
    null("the two measures are told apart: twelve at twice do not pass two's -44 dB", not many < -44, "%.1f dB" % many)

    # --- the caps come down on their own and go up only when asked ---
    r = go(["gen 44100"] + setall({"shape": "ramp", "unison": 7, "fmIndex": 2, "syncRatio": 1.5})
           + ["set releaseMs 150", "voices 0 " + chord(36), "run 2205", "voices 0 " + chord(60), "run 128", "budget",
              # The releases die away over the next half second; the chord is
              # the same. Then one block more, since the budget is asked once
              # a block: read straight after, a cap that rose the moment they
              # went passed.
              "run 22050", "run 128", "budget",
              # The same chord, struck again: a chord change, so the caps are free.
              "voices 0 " + chord(60), "run 128", "budget",
              # And a setting moved, down and back up, with the chord held.
              "voices 0 " + chord(36), "run 128", "voices 0 " + chord(60), "run 128", "budget",
              "run 22050", "set unison 5", "run 128", "set unison 7", "run 128", "budget"])
    crowded, after, struck, again, moved = r.budgets
    print("    crowded %d, after %d (%d voices), struck %d, crowded again %d, moved %d"
          % (crowded["unison"][0], after["unison"][0], after["voices"][0], struck["unison"][0], again["unison"][0], moved["unison"][0]))
    check("with releases in flight, the chord has fewer copies than it asked for", crowded["unison"][0] < 7, str(crowded))
    check("and keeps them as the releases die away under the same chord",
          after["voices"][0] == 8 and after["unison"][0] == crowded["unison"][0], str(after))
    null("the releases had gone, so the cap could have crept back", after["voices"][0] < crowded["voices"][0], str(crowded["voices"]))
    check("striking the chord again gives them back", struck["unison"][0] > crowded["unison"][0], str(struck))
    check("and so does moving the unison asked for", again["unison"][0] < moved["unison"][0], str((again, moved)))

    # --- a note let go fades ---
    # Sines at one to two hertz barely move from one sample to the next, so
    # a step is plain. Folded at four times with seven copies and FM, it is
    # dear enough that a chord over releases has some let go.
    cfg = {"shape": "sine", "unison": 7, "fmIndex": 1, "fold": 0.3, "shapeOS": 4, "vcfType": 1, "vcfCutoff": 2000,
           "releaseMs": 10000, "attackMs": 200}
    r = go(["gen 44100"] + ["set %s %s" % kv for kv in cfg.items()]
           + ["voices 0 " + chord(36, 1), "run 13230", "voices 0 " + chord(60, 1.3), "heard 64", "pool", "heard 2141", "heard 2205"])
    cut = sum(1 for v in r.pools[0] if v["cut"])
    heard = np.concatenate(r.heard[:2])
    most, steady = float(np.max(np.abs(np.diff(heard)))), float(np.max(np.abs(np.diff(r.heard[2]))))
    print("    %d let go; largest move a sample %.4f, then %.4f" % (cut, most, steady))
    check("a chord over releases has some let go", cut > 0, str(cut))
    # Faded over ten milliseconds, the voices move the sum by 0.002 a sample
    # at most; cut in one sample, by what they were worth, 0.3 or more.
    check("and the sum never steps as they go: its largest move a sample stays under 0.01", most < 0.01, "%.4f" % most)
    # The null: the same voices cut in one sample, by what the fade removed -
    # the largest the let-go voices together were worth in a sample.
    gone = go(["gen 44100"] + ["set %s %s" % kv for kv in cfg.items()]
              + ["voices 0 " + chord(36, 1), "run 13230", "heard 1"]).heard[0]
    null("a cut in one sample would step by what the voices were worth, far past 0.01", float(np.max(np.abs(gone))) > 0.01,
         "%.3f" % float(np.max(np.abs(gone))))

    # --- ordinary playing ---
    # The old library, from before P8g, and then the bank: the old one is the
    # widest set of real setups there is, and the bank is what is played now,
    # each restored by the core's own restoreSetup. On ?brain=js each was
    # loaded on the page and its genSettings copied into a fresh page core;
    # here the setup goes into the core whole. The page's scan copied the
    # generator's fields and no routings, so a routing onto FM, sync or the
    # shaper, which the model costs, was never counted; that check is kept as
    # it was, and a second, with each setup's routings from the core's own
    # matrix, holds the bank, which is what is played now. With routings one
    # setup of the old library does give something up (Glass pad: its
    # env.note>gen.fm makes both hands' five copies four), which the page's
    # brain did too and the page's scan could not see.
    with open(LIBRARY, encoding="utf-8") as f:
        library = json.load(f)
    loads = [("c:" + name, "setup " + json.dumps(setup)) for _, entries, _ in library for name, setup, *_ in entries]
    bank = int(subprocess.run([kit.build("budget_cpp"), "--bank"], check=True, capture_output=True, text=True).stdout)
    loads += [("b:%d" % k, "preset %d" % k) for k in range(bank)]
    seen, shapes, governed, routed, dearest = 0, set(), [], [], (0, "")
    for name, load in loads:
        info = go([load, "shape", "layered"])
        if "shape" not in info.words: continue
        layered = info.words["layered"] == ["1"]
        played = ["voices 0 " + chord(48)] + (["voices 1 " + chord(60)] if layered else []) + ["run 128", "budget"]
        b = go([load] + played).budgets[0]
        if thinned(go([load, "routes"] + played).budgets[0], layered): routed.append(name)
        seen += 1; shapes.add(info.words["shape"][0])
        if b["units"] > dearest[0]: dearest = (b["units"], name)
        if thinned(b, layered): governed.append(name)
    print("    %d setups, %d shapes among them; the dearest %s at %.1f" % (seen, len(shapes), dearest[1], dearest[0]))
    # The shapes counted because the first version of this scan, on the
    # page, loaded each preset by its bare name, found none of them, and
    # measured the default tone 169 times - passing, whatever the budget was.
    check("the scan read the presets it names: more than a hundred, in more than six shapes",
          seen > 100 and len(shapes) > 6, "%d, %d shapes" % (seen, len(shapes)))
    check("no preset gives anything up under a chord of eight on each layer it plays", governed == [], str(governed[:6]))
    print("    with their routings: %s give something up" % routed)
    check("and the bank gives nothing up with its routings counted too", [n for n in routed if n.startswith("b:")] == [], str(routed))
    null("with its routings counted, the old library's Glass pad does give something up, so the count can see one",
         "c:Glass pad" in routed, str(routed))
    # Its null: the dearest preset, with two copies more a layer than it asks,
    # is given up on - so the scan's chord is near enough the budget to fail.
    dear_load = dict(loads)[dearest[1]]
    r = go([dear_load, "layered", "voices 0 " + chord(48), "voices 1 " + chord(60), "set unison 7", "set unison 7 1",
            "set drive 0.5", "set drive 0.5 1", "run 128", "budget"])
    null("the dearest preset with seven copies and drive on both layers is thinned", thinned(r.budgets[0]), str(r.budgets[0]))
