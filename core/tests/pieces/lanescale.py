"""Lanes three to six have a full scale in the instrument (15 Nov).

Until 15 Nov the core registered `view.scale1` and `view.scale2` as
destinations and no others (`screen.h`), so a routing onto lane three or
four's full scale - which a split drawing a figure a hand offers, B's figure
being lanes three and four - was heard by nothing, and since stage 5 moved
nothing on the face either. The owner's decision (after-stage-5.md, 15 Nov):
register them. No bank preset and no setup in the old library routes them,
so nothing already saved changes.

Rendered here as a split, each hand drawing its own figure, a chord in each,
Scan reading each hand's own picture at its top and the Picture amount at
nought, so what moves a hand's timbre is Scan alone. Two runs: nothing
routed, and LFO 1 on lane three's full scale. Read twice: B's own grid (what the instrument draws for the upper
hand), and B's Scan table (what it reads off that picture). The routing on
lane three must move both of B's against the plain run and leave A's grid
alone. Lane one is no null for that: it is the trigger's lane, so scaling it
moves where every lane's window is cut, B's included (its routing moves B's
grid and table too, which the first draft of this piece expected not to).
The null is the core as it was, built here with only the first two lanes
registered: the same routing on lane three moves nothing of B's.
"""
import os, shutil, subprocess
import base64, json

import numpy as np


def code(setup):
    return base64.b64encode(json.dumps(setup).encode()).decode().rstrip("=")


SPLIT = {"v": 11, "display": "xy", "midiMode": "poly", "layers": "split", "splitAt": 60, "layerPair": "each",
         "shape": "sine", "bShape": "sine", "freq": 220, "oscScan": 100, "bScan": 100, "scanReadsA": "A", "scanReadsB": "B",
         "pictureAmount": 0, "bPictureAmount": 0, "persistence": "0.12", "l0r": 40, "l0a": 100, "polyRound": True}


def old_core(kit):
    """render_cpp built against a copy of the core registering lanes one and two only, as until 15 Nov."""
    from pieces import kit as kitmod
    root = os.path.join(kitmod.BUILD, "lanescale-two")
    if os.path.isdir(root): shutil.rmtree(root)
    shutil.copytree(kitmod.INCLUDE, os.path.join(root, "include"))
    path = os.path.join(root, "include", "scope", "screen.h")
    text = open(path).read()
    old = "i < static_cast<std::size_t>(kMaxLanes); i++"
    assert text.count(old) == 1
    open(path, "w").write(text.replace(old, "i < 2; i++"))
    exe = os.path.join(root, "render_two")
    subprocess.run(["g++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror", "-I", os.path.join(root, "include"),
                    os.path.join(kitmod.HERE, "tools", "render_cpp.cpp"), "-o", exe], check=True)
    return exe


def run_of(kit, routing, exe=None):
    lines = [["make", 48000, code(SPLIT)]]
    if routing: lines.append(["routings", routing])
    lines += [["midi", 0x90, 48, 100], ["midi", 0x90, 55, 100], ["midi", 0x90, 72, 100], ["midi", 0x90, 79, 100],
              ["to", 1.0], ["every", 0.1, "lgrid", "table"], ["to", 5.0]]
    if exe:
        built = kit._built.get("render_cpp")
        kit._built["render_cpp"] = exe
        try: rows = kit.render(lines)
        finally:
            if built: kit._built["render_cpp"] = built
            else: kit._built.pop("render_cpp")
    else:
        rows = kit.render(lines)
    grid = np.array([[float(v) for v in r["lgrid"]] for r in rows])          # A's two sums, then B's
    table = {k: [np.array(r["table" + k]) for r in rows if r.get("table" + k)] for k in "AB"}
    return grid, table


def apart(a, b):
    """The mean distance between two runs' readings, reading by reading."""
    if isinstance(a, list): return float(np.mean([np.mean(np.abs(x - y)) for x, y in zip(a, b)])) if a and b else 0.0
    return float(np.mean(np.abs(a - b)))


def run(kit):
    check, null = kit.check, kit.null
    plain, three = run_of(kit, ""), run_of(kit, "lfo1>view.scale3@1")
    two = old_core(kit)
    old_plain, old_three = run_of(kit, "", two), run_of(kit, "lfo1>view.scale3@1", two)
    gB, tB = apart(three[0][:, 2:], plain[0][:, 2:]), apart(three[1]["B"], plain[1]["B"])
    gA = apart(three[0][:, :2], plain[0][:, :2])
    oB, otB = apart(old_three[0][:, 2:], old_plain[0][:, 2:]), apart(old_three[1]["B"], old_plain[1]["B"])
    print("    lane three routed: B's grid moved %.4g, B's Scan table %.4g, A's grid %.4g; on the old core B's grid %.4g, table %.4g"
          % (gB, tB, gA, oB, otB))
    check("a routing onto lane three's full scale moves what the instrument draws for the upper hand and what Scan reads off it",
          gB > 1.0 and tB > 1e-3, "grid %.4g, table %.4g" % (gB, tB))
    check("and leaves the lower hand's figure as it was", gA == 0, "%.4g" % gA)
    null("on the core as it was, lanes one and two registered alone, the same routing moves nothing of the upper hand's",
         not (oB > 1.0 and otB > 1e-3), "grid %.4g, table %.4g" % (oB, otB))
