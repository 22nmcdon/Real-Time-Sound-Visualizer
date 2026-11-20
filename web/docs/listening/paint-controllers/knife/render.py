"""The bend as a palette knife (20 Nov): pictures for the owner before its
checks. The bend phrase from the paint-controllers page (a whole tone up in a
quarter second and back, then down slowly over a second and back), painted by
the core and drawn by the face's own look:

  bend-knife-REACH.jpg   the knife at 0.7, 1.0 (its default) and 1.5 of its reach
  bend-smear.jpg         0ad2682's smear (SMEAR=, that commit's core unpacked)
  bend-without.jpg       the brush deaf to the bend
  bend-WAY-flick.jpg     each close round the quick bend, and bend-WAY-slow.jpg round the slow one
  bend-knife-1.0-map.png the core's map of the default, at its own cells, and its close-ups beside the look's

    CHROME=/opt/pw-browsers/chromium FIRST=/path/to/7389e9c SMEAR=/path/to/0ad2682 \\
        python3 web/docs/listening/paint-controllers/knife/render.py
"""
import importlib.util, json, os, subprocess

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("controllers", os.path.join(HERE, "..", "render.py"))
ctl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ctl)
pw, step1 = ctl.pw, ctl.step1
BUILD = os.path.join(ctl.BUILD, "knife")
SMEAR = os.environ.get("SMEAR", "")


def box(x, y, h):
    return (max(0, x - h), max(0, y - h), min(1, x + h), min(1, y + h))


def main():
    os.makedirs(BUILD, exist_ok=True)
    ctl.build()
    if SMEAR:
        subprocess.run(["g++", "-std=c++17", "-O2", "-I", os.path.join(SMEAR, "core", "include"),
                        os.path.join(SMEAR, "web", "docs", "listening", "paint-controllers", "render.cpp"), "-o",
                        os.path.join(BUILD, "render-smear")], check=True)
    _, setup, make, _ = ctl.PHRASES["bend"]
    notes, events, length = make()
    path = os.path.join(BUILD, "bend.script")
    with open(path, "w") as f: f.write(ctl.script(json.dumps(setup), notes, events, length))
    out = lambda n: os.path.join(HERE, n)
    ways = [("knife-1.0", "render", ("2", "15", "0", "1")), ("knife-0.7", "render", ("2", "15", "0", "0.7")),
            ("knife-1.5", "render", ("2", "15", "0", "1.5")), ("without", "render", ("2", "11", "0"))]
    if SMEAR: ways.append(("smear", "render-smear", ("2", "15", "0", "0", "1")))
    looks = pw.Looks()
    boxes = None
    try:
        for way, tool, args in ways:
            prefix = os.path.join(BUILD, "bend-" + way)
            exe = os.path.join(ctl.BUILD, tool) if tool == "render" else os.path.join(BUILD, tool)
            subprocess.run([exe, path, prefix] + list(args), check=True)
            if boxes is None:
                # Where the knife works in the quick bend and in the slow one: its stamps in each window.
                _, S = pw.stamps_of(prefix, 23)
                K = S[S[:, 20] == 2]
                def at(t0, t1):
                    q = K[(K[:, 6] >= t0) & (K[:, 6] <= t1)]
                    return (float(np.median(q[:, 0])), float(np.median(q[:, 1]))) if len(q) else (0.5, 0.5)
                boxes = {"flick": box(*at(1.0, 1.5), 0.14), "slow": box(*at(3.8, 5.0), 0.17)}
            crops = [(boxes[k], out("bend-%s-%s.jpg" % (way, k))) for k in ("flick", "slow")]
            looks.look(prefix, out("bend-%s.jpg" % way), floats=23, crop=crops)
            if way == "knife-1.0":
                _, thick, wet = step1.maps_of(prefix)
                m = step1.picture(thick[-1], wet[-1], size=768)
                m.save(out("bend-knife-1.0-map.png"), optimize=True)
                for k in ("flick", "slow"):
                    px = tuple(int(round(v * 768)) for v in boxes[k])
                    m.crop(px).resize(((px[2] - px[0]) * 2, (px[3] - px[1]) * 2), Image.NEAREST).save(out("bend-knife-1.0-%s-map.png" % k), optimize=True)
    finally:
        looks.close()


if __name__ == "__main__":
    main()
