"""The bend as a palette knife (20 Nov): pictures for the owner before its
checks. The bend phrase from the paint-controllers page (a whole tone up in a
quarter second and back, then down slowly over a second and back), painted by
the core and drawn by the face's own look. Second design: the knife displaces
and levels the stroke's own paint (a slab, a film behind, a lip ahead), where
2da8bfd laid a separate sheet beside it.

  bend-knife-REACH.jpg   the knife at 1.0 (its default) and 1.5 of its reach
  bend-sheet.jpg         2da8bfd's knife, a sheet laid beside the stroke (SHEET=, that commit's core unpacked)
  bend-without.jpg       the brush deaf to the bend
  bend-WAY-flick.jpg     each close round the quick bend, and bend-WAY-slow.jpg round the slow one
  bend-knife-1.0-map.png the core's map of the default, at its own cells, and its close-ups beside the look's
  flick-large.jpg        the default's quick bend at three times the look's pixels

    CHROME=/opt/pw-browsers/chromium FIRST=/path/to/7389e9c SHEET=/path/to/2da8bfd \\
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
SMEAR = os.environ.get("SHEET", "")


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
    # The swath the strokes' full width, and seven tenths of it so a strip of the stroke survives each side.
    # The full-width knife the owner chose at a710a49; its seven-tenths variant went from the build after (the pictures stay).
    ways = [("knife-full", "render", ("2", "15", "0")), ("without", "render", ("2", "11", "0"))]
    # 5ece483's knife is not rendered here: its stamps mean something else to today's shader. Its own pictures, from
    # that commit, are kept beside these as bend-5ece483*.jpg and 5ece483-flick-large.jpg.
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
            if way.startswith("knife"):
                # The flick at three times: its own box, a little tighter, upscaled from the whole look after.
                fb = boxes["flick"]
                cxy = ((fb[0] + fb[2]) / 2, (fb[1] + fb[3]) / 2)
                large = box(cxy[0], cxy[1], 0.09)
            looks.look(prefix, out("bend-%s.jpg" % way), floats=23, crop=crops)
            if way.startswith("knife"):
                img = Image.open(out("bend-%s.jpg" % way))
                n = img.size[0]
                px = tuple(int(round(v * n)) for v in large)
                img.crop(px).resize(((px[2] - px[0]) * 3, (px[3] - px[1]) * 3), Image.LANCZOS).save(out("%s-flick-large.jpg" % way), quality=92)
            if way == "knife-full":
                _, thick, wet = step1.maps_of(prefix)
                m = step1.picture(thick[-1], wet[-1], size=768)
                m.save(out("bend-knife-full-map.png"), optimize=True)
                for k in ("flick", "slow"):
                    px = tuple(int(round(v * 768)) for v in boxes[k])
                    m.crop(px).resize(((px[2] - px[0]) * 2, (px[3] - px[1]) * 2), Image.NEAREST).save(out("bend-knife-full-%s-map.png" % k), optimize=True)
    finally:
        looks.close()


if __name__ == "__main__":
    main()
