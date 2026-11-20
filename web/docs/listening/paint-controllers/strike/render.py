"""The hard strike, second design (20 Nov): a prototype for the owner to look at
before its checks are finished. A brush slammed onto the canvas splays - a fan
of clumped bristles from a heavy heel, then the stroke after running as
separate tracks that regather - in place of the drops of spatter. Pictures
only, beside the paint-controllers page:

  sheet-N.jpg          (a) six hard strikes (velocity 127, Strike 100) on different notes, each with about a second
                       of the stroke after: similar, never the same
  ladder-VEL.jpg       (b) velocity 30, 60, 90, 110 and 127 at Strike 100, each with its stroke after
  phrase-WAY.jpg       (c) the listening page's strikes phrase: `splay` (this design), `flecks` (the same with the
                       hardest strikes flicking a few flecks off the fingers), `drops` (b0c1db9), `first` (7389e9c)
                       and `without` (no mark at all); a close-up round its first hard strike each, and the whole look
  single-look.jpg      (d) one strike close up, and single-map.png the core's map of the same box
  single-map.png
  bend-WAY.jpg         (e) the bend phrase (a whole tone up in a quarter second and back, then down slowly over a
                       second and back): `pull` (the redesigned pull), `pull-short` and `pull-long` (its reach at 0.6
                       and 1.6 times), `without`, and `smear` (b0c1db9's); bend-WAY-flick.jpg and bend-WAY-slow.jpg
                       close-ups of the flick and the slow bend, and bend-pull-map.png the core's map

switch-play-*.png, from switch-mock.py beside this file, are where the wheel's and pressure's Sound / Brush / Both
switch would go on Play, mocked into the page for the picture only (nothing of it is built).

    CHROME=/opt/pw-browsers/chromium FIRST=/path/to/7389e9c DROPS=/path/to/b0c1db9 \\
        python3 web/docs/listening/paint-controllers/strike/render.py

FIRST and DROPS are those commits' core/include and the paint-controllers render.cpp, unpacked
(`git archive COMMIT core/include web/docs/listening/paint-controllers/render.cpp | tar -x -C DIR`).
"""
import importlib.util, json, os, subprocess, sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("controllers", os.path.join(HERE, "..", "render.py"))
ctl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ctl)
pw, step1 = ctl.pw, ctl.step1
BUILD = os.path.join(ctl.BUILD, "strike")
DROPS = os.environ.get("DROPS", "")

STRUCK = dict(ctl.STRUCK, sus=70)  # a held tone, so the stroke after the strike goes on a second


def build():
    os.makedirs(BUILD, exist_ok=True)
    ctl.build()
    if not DROPS: raise SystemExit("DROPS: the core as of b0c1db9, unpacked; see the top of this file")
    subprocess.run(["g++", "-std=c++17", "-O2", "-I", os.path.join(DROPS, "core", "include"),
                    os.path.join(DROPS, "web", "docs", "listening", "paint-controllers", "render.cpp"), "-o",
                    os.path.join(BUILD, "render-drops")], check=True)


def run(name, setup, notes, length, tool="render", args=("2", "15", "-1")):
    path = os.path.join(BUILD, name + ".script")
    with open(path, "w") as f: f.write(ctl.script(json.dumps(setup), notes, [], length))
    prefix = os.path.join(BUILD, name)
    exe = os.path.join(ctl.BUILD, tool) if tool in ("render", "render-first") else os.path.join(BUILD, tool)
    subprocess.run([exe, path, prefix] + list(args), check=True)
    return prefix


def heels(prefix):
    """Where each hard strike landed: each serial that laid a mark (a finger, kind 3), its first brush stamp, in the
    unit square, in time order."""
    _, S = pw.stamps_of(prefix, 23)
    marked = {int(r[16]) for r in S if r[20] == 3}
    seen, out = set(), []
    for r in S:
        if r[20] == 0 and int(r[16]) in marked and int(r[16]) not in seen:
            seen.add(int(r[16])); out.append((float(r[0]), float(r[1])))
    return out


def box(x, y, h=0.1):
    return (max(0, x - h), max(0, y - h), min(1, x + h), min(1, y + h))


def main(parts):
    build()
    looks = pw.Looks()
    out = lambda n: os.path.join(HERE, n)
    try:
      if "a" in parts:
        # (a) six hard strikes on different notes, 1.4 s apart, each held a second.
        notes = [(0.2 + 1.4 * i, n, 127, 1.0) for i, n in enumerate((48, 57, 62, 67, 72, 79))]
        pre = run("sheet", STRUCK, notes, 9.0)
        crops = [(box(x, y, 0.12), out("sheet-%d.jpg" % (i + 1))) for i, (x, y) in enumerate(heels(pre))]
        looks.look(pre, out("sheet-look.jpg"), floats=23, crop=crops)
      if "b" in parts:
        # (b) the velocity ladder, on notes apart so they do not overlap.
        ladder = (30, 60, 90, 110, 127)
        notes = [(0.2 + 1.4 * i, 55 + 5 * i, v, 1.0) for i, v in enumerate(ladder)]
        pre = run("ladder", STRUCK, notes, 7.6)
        at = heels(pre)
        # A soft strike has no heel to find: its place is the layout's, the note at its moment.
        _, S = pw.stamps_of(pre, 23)
        firsts = {}
        for r in S:
            firsts.setdefault(int(r[16]), (float(r[0]), float(r[1])))
        spots = list(firsts.values())[:len(ladder)]
        crops = [(box(x, y, 0.12), out("ladder-%d.jpg" % v)) for v, (x, y) in zip(ladder, spots)]
        looks.look(pre, out("ladder-look.jpg"), floats=23, crop=crops)
      if "c" in parts:
        # (c) the strikes phrase, five ways, cropped alike round its first hard strike.
        _, setup, make, _ = ctl.PHRASES["strikes"]
        notes, _, length = make()
        ways = [("splay", "render", ("2", "15", "-1"), 23), ("flecks", "render", ("2", "15", "-1", "1"), 23),
                ("drops", "render-drops", ("2", "15", "-1"), 23), ("first", "render-first", ("2", "15", "-1"), 20),
                ("without", "render", ("2", "15", "0"), 23)]
        first_box = None
        for way, tool, args, floats in ways:
            pre = run("phrase-" + way, setup, notes, length, tool, args)
            if first_box is None:
                # The first hard strike: where its longest finger is rooted (the phrase is one joined stroke, one serial,
                # and every strike marks, the soft barely, so the longest finger is the hard strike's).
                _, S = pw.stamps_of(pre, 23)
                fingers = S[S[:, 20] == 3]
                best = float((fingers[:, 4] * fingers[:, 21]).max())
                r = next(r for r in fingers if float(r[4] * r[21]) >= 0.8 * best)
                x, y = float(r[0]), float(r[1])
                first_box = box(x, y, 0.11)
            looks.look(pre, out("phrase-%s.jpg" % way), floats=floats, crop=(first_box, out("phrase-%s-close.jpg" % way)))
      if "e" in parts:
        # (e) the bend phrase (up a whole tone in a quarter second and back, then down slowly over a second and back):
        # the redesigned pull at three reaches, without, and b0c1db9's smear; close-ups of the flick and the slow bend.
        _, setup, make, _ = ctl.PHRASES["bend"]
        notes, events, length = make()
        path = os.path.join(BUILD, "bend.script")
        with open(path, "w") as f: f.write(ctl.script(json.dumps(setup), notes, events, length))
        boxes = None
        for way, tool, args in [("pull", "render", ("2", "15", "0", "0", "1")), ("pull-short", "render", ("2", "15", "0", "0", "0.6")),
                                ("pull-long", "render", ("2", "15", "0", "0", "1.6")), ("without", "render", ("2", "11", "0")),
                                ("smear", "render-drops", ("2", "15", "0"))]:
            prefix = os.path.join(BUILD, "bend-" + way)
            exe = os.path.join(ctl.BUILD, tool) if tool == "render" else os.path.join(BUILD, tool)
            subprocess.run([exe, path, prefix] + list(args), check=True)
            if boxes is None:
                # Where the flick's streaks start and where the slow bend's do: the pull stamps in each window.
                _, S = pw.stamps_of(prefix, 23)
                P = S[S[:, 20] == 2]
                def at(t0, t1):
                    q = P[(P[:, 6] >= t0) & (P[:, 6] <= t1)]
                    return (float(np.median(q[:, 0])), float(np.median(q[:, 1]))) if len(q) else (0.5, 0.5)
                boxes = {"flick": box(*at(1.0, 1.3), 0.13), "slow": box(*at(3.8, 4.8), 0.16)}
            crops = [(boxes[k], out("bend-%s-%s.jpg" % (way, k))) for k in ("flick", "slow")]
            looks.look(prefix, out("bend-%s.jpg" % way), floats=23 if tool == "render" else 23, crop=crops)
            if way == "pull":
                _, thick, wet = step1.maps_of(prefix)
                step1.picture(thick[-1], wet[-1]).save(out("bend-pull-map.png"), optimize=True)
      if "d" in parts:
        # (d) one strike close up, beside the map of the same box.
        pre = run("single", STRUCK, [(0.2, 60, 127, 1.0)], 1.6)
        (x, y), = heels(pre)[:1]
        b = box(x, y, 0.1)
        looks.look(pre, out("single-full.jpg"), floats=23, crop=(b, out("single-look.jpg")))
        _, thick, wet = step1.maps_of(pre)
        m = step1.picture(thick[-1], wet[-1], size=768)
        px = tuple(int(round(v * 768)) for v in b)
        m.crop(px).resize(((px[2] - px[0]) * 2, (px[3] - px[1]) * 2), Image.NEAREST).save(out("single-map.png"), optimize=True)
    finally:
        looks.close()


if __name__ == "__main__":
    main(sys.argv[1:] or ["a", "b", "c", "d", "e"])
