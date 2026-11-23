"""The zoom is only the look (22 Nov, the owner's: "I don't think zoom should
affect the sound anymore. It feels wrong"). Until then the beam magnified what
it laid into the grid by the zoom (scope/beam.h), and Scan, the picture's
sources and the photocell read that grid, so a zoom changed the sound - by
0.646 of the spectrum's distance at its worst in the reach audit. Now the face
magnifies its own drawing, and the grid is laid whole at any zoom.

What would go wrong, and what is checked for it, each with its null:

- the zoom still reaching the sound: a Breathing preset (Scan at work, the
  loop open) held under a chord, in X-Y and in Y-T, at the zoom's step 0 and at
  8, 16 and 24 (1x, 4x, 16x, 64x): the heard pair and the grid Scan reads the
  same to the bit as at 1x. The null: a copy of the core with the old beam,
  which magnified the deposit, reads a different grid and a different sound
  at 16x in both displays;
- a routing on the zoom reaching it the other way: LFO 1 on view.zoom at full
  depth leaves the sound and the grid as with no routing. The null is the
  old beam under the same routing;
- the zoom being dropped rather than kept as the look: a routing on it still
  moves the zoom the instrument reports in its view's readings, which the face
  draws the magnified screen by; the null is the same reading with no routing.
"""
import base64, json, os, re, shutil, subprocess

import numpy as np

from pieces.kit import BUILD, HERE, INCLUDE

RATE = 48000
CHORD = [48, 55, 64]


def bank():
    text = open(os.path.join(INCLUDE, "scope", "presets.h"), encoding="utf-8").read()
    lib = json.loads("".join(re.findall(r'R"preset\((.*?)\)preset"', text, re.S)))
    version = int(re.search(r"kSetupVersion = (\d+)", open(os.path.join(INCLUDE, "scope", "setup.h")).read()).group(1))
    return {e[0]: e[1] for s in lib for e in s[1]}, version


def code(setup, version):
    return base64.b64encode(json.dumps(dict(setup, v=version)).encode()).decode().rstrip("=")


def old_beam():
    """render_cpp against a copy of the core whose beam magnifies its deposit, as before 22 Nov."""
    root = os.path.join(BUILD, "zoom-old")
    if os.path.isdir(root): shutil.rmtree(root)
    shutil.copytree(INCLUDE, os.path.join(root, "include"))
    path = os.path.join(root, "include", "scope", "beam.h")
    text = open(path, encoding="utf-8").read()
    for a, b in (("    const double scale = radius;  // never the zoom: see Screen::zoom\n", "    const double scale = radius * s.zoom;\n"),
                 ("  const double visible = std::fmax(16.0, f.length);", "  const double visible = std::fmax(16.0, jsRound(f.length / s.zoom));")):
        assert text.count(a) == 1, "beam.h: not where the piece expects it: " + a
        text = text.replace(a, b)
    open(path, "w", encoding="utf-8").write(text)
    exe = os.path.join(root, "render_oldzoom")
    subprocess.run(["g++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror", "-I", os.path.join(root, "include"),
                    os.path.join(HERE, "tools", "render_cpp.cpp"), "-o", exe], check=True)
    return exe


def play(exe, setup_code, before):
    """The heard pair, the grid at 2.5 s, and the view's readings, for a chord held from 0.5 s after `before`."""
    tag = "%d-%d" % (os.getpid(), abs(hash((exe, setup_code, json.dumps(before)))) % 10**9)
    heard, grid, script = (os.path.join(BUILD, "zoom-%s.%s" % (tag, x)) for x in ("heard", "grid", "txt"))
    lines = [["make", RATE, setup_code]] + before + [["record", "heard", heard], ["record", "grid", grid], ["to", 0.5]] \
        + [["midi", 0x90, n, 100] for n in CHORD] + [["to", 2.5], ["read", "griddump", "loop"], ["to", 3.0]]
    with open(script, "w") as f: f.write("\n".join(json.dumps(l) for l in lines) + "\n")
    out = subprocess.run([exe, script], check=True, capture_output=True, text=True).stdout
    x, g = np.fromfile(heard, dtype=np.float32), np.fromfile(grid, dtype=np.float32)
    for p in (heard, grid, script):
        if os.path.exists(p): os.remove(p)
    loop = next((l.split() for l in out.split("\n") if l.startswith("loop ")), [])
    return x, g, loop


def same(a, b):
    return len(a) == len(b) and len(a) > 0 and np.array_equal(a, b)


def run(kit):
    check, null = kit.check, kit.null
    presets, version = bank()
    name = next(n for n, s in presets.items() if s.get("pictureAmount", 60) > 0 and s.get("oscScan", 0) > 0)
    render, old = kit.build("render_cpp"), old_beam()
    for display in ("xy", "yt"):
        c = code(dict(presets[name], display=display), version)
        base = play(render, c, [])
        for step in (8, 16, 24):
            got = play(render, c, [["slider", "zoom", str(step)]])
            check("%s in %s at zoom %gx: the sound and the grid Scan reads are as at 1x, to the bit" % (name, display, 2 ** (step / 4)),
                  same(got[0], base[0]) and same(got[1], base[1]), "%d samples, %d cells" % (len(got[0]), len(got[1])))
        was, was_zoomed = play(old, c, []), play(old, c, [["slider", "zoom", "16"]])
        null("%s in %s: the old beam at 16x lays another grid and plays another sound" % (name, display),
             not same(was_zoomed[1], was[1]) and not same(was_zoomed[0], was[0]),
             "largest sound difference %.3g" % float(np.max(np.abs(was_zoomed[0].astype(float) - was[0].astype(float)))))
        if display == "xy":
            routed = [["routings", "lfo1>view.zoom@1"]]
            got = play(render, c, routed)
            check("%s: LFO 1 on the zoom at full depth leaves the sound and the grid as with no routing" % name,
                  same(got[0], base[0]) and same(got[1], base[1]))
            null("%s: the old beam under the same routing plays another sound" % name, not same(play(old, c, routed)[0], was[0]))
    # Kept as the look: a routing on the zoom still moves it in the view the instrument reports,
    # which the face draws the magnified screen by.
    def zoom_offset(lines):
        rows = kit.render([["make", RATE, code(presets[name], version)]] + lines + [["to", 1.3], ["read", "loop"]])
        words = rows[-1].get("loop", []) if rows else []
        return float(words[words.index("visual") + 3]) if "visual" in words else None
    moved, still = zoom_offset([["routings", "lfo1>view.zoom@1"]]), zoom_offset([])
    check("the zoom is kept as the look: LFO 1 on it still moves the zoom the instrument reports to the face",
          moved is not None and abs(moved) > 0.1, "offset %s" % moved)
    null("with no routing the reported offset is nought", still == 0.0, "offset %s" % still)
