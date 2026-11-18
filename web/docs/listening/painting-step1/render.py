"""Painting, step 1: the study's four phrases played offline by the core, on the
trace and painting, for the owner to judge by ear before anything is live.

The phrases are the painting study's (`claude/painting-study`,
web/docs/painting-study/tools/phrases.py), copied here as they were so the
two can be compared: a held pad, the owner's Crossed hands, a fast run and a
chord change, each a setup code and a timed list of notes, played a
128-frame block at a time at 48 kHz with a note landing at the top of the
block it falls in. Each is rendered three ways by render.cpp beside this
file, the instrument itself:

  trace    as the instrument ships: Scan and the Picture amount read the trace
  paint    painting, the owner's drying (thin paint 2 s, a thick stroke 6 s)
  slow     painting, drying three times slower (6 s and 18 s), past a turn

and measured as the study measured Scan (painting-the-sound.md, What Scan
reads off each): each table's harmonic centroid, and how far it moves from
one frame to the next. Painting reads one table a note, so its numbers are
over every sounding note's table; the trace's over each hand's.

Writes beside this file: results.json; audio/NAME-VERSION.mp3 (64 kbps
stereo); pictures/NAME-VERSION.png (the map at the phrase's end, thickness
in greys and wet paint in blue) and pictures/NAME-VERSION-strip.png (eight
moments across the phrase). Build products go in core/build/listening/.

    python3 web/docs/listening/painting-step1/render.py [NAME ...]
"""
import json, math, os, random, subprocess, sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
CORE = os.path.join(ROOT, "core")
BUILD = os.path.join(CORE, "build", "listening", "painting-step1")
RATE, BLOCK, N = 48000, 128, 128

# The owner's repeatable Crossed hands (the-picture-amount.md), as the study played it.
CROSSED = ("eyJ2IjoxMCwic2hhcGUiOiJzaW5lIiwib3NjU2NhbiI6MTAwLCJzY2FuUmVhZHNBIjoiQiIsInNjYW5SZWFkc0IiOiJBIiwiZnJlcSI6MTEwLCJjeWNsZXMiOiIiLCJkaXNwbGF5IjoieHkiLCJwZXJzaXN0ZW5jZSI6IjAuMDI1NSIsIm1pZGlNb2RlIjoicG9seSIsInBvbHlSb3VuZCI6dHJ1ZSwibGF5ZXJzIjoic3BsaXQiLCJwaWN0dXJlQW1vdW50Ijo0NywiZGVsYXlNaXgiOjM1LCJkZWxheUZlZWRiYWNrIjo0NywicGhhc2VyTWl4IjozMCwicmV2ZXJiTWl4IjoyNn0")

VERSIONS = {
    "trace": None,
    "paint": (2.0, 6.0),
    "slow": (6.0, 18.0),
}


def held_pad():
    return [(0.25, n, 80, 9.0) for n in (48, 55, 62, 64, 71)], 12.0


def crossed_hands():
    notes = [(0.3, n, 70, 3.7) for n in (37, 44, 48)]
    notes += [(4.0, n, 70, 9.0) for n in (42, 49, 53)]
    scale = [61, 63, 65, 68, 70, 72, 73, 75, 77]
    run = scale + scale[-2:0:-1]
    t, i = 1.0, 0
    while t < 6.0:
        fast = t >= 2.6
        step = 1 / 8 if fast else 1 / 5
        notes.append((t, run[i % len(run)], 95 if fast else 55, step * 0.9))
        t += step; i += 1
    notes += [(8.0, 70, 40, 0.07), (8.07, 72, 40, 1.0)]
    notes += [(9.6, 66, 40, 0.07), (9.67, 68, 40, 2.6)]
    return notes, 15.5


def fast_run():
    rnd = random.Random(7)
    up = [60, 62, 64, 65, 67, 69, 71, 72]
    path = up + up[-2::-1][:-1]
    notes, t = [], 0.3
    for p in range(3):
        for k, n in enumerate(path):
            arch = 1 - abs(k - 7) / 7
            vel = int(max(20, min(127, 45 + 70 * arch + rnd.uniform(-12, 12) + 10 * p)))
            notes.append((t, n, vel, 0.1))
            t += 1 / 9
    notes.append((t, 60, 100, 1.2))
    return notes, t + 2.2


def chord_change():
    chords = [(50, 53, 57, 60), (43, 53, 59, 62), (48, 52, 55, 59), (45, 52, 55, 60)]
    notes = []
    for k, ch in enumerate(chords):
        for n in ch: notes.append((0.3 + 2.5 * k, n, 78, 2.4))
    return notes, 11.6


PHRASES = {
    "pad": ("Held pad", "Slow pad", held_pad),
    "crossed": ("Crossed hands", None, crossed_hands),
    "run": ("Fast run", "Tine piano", fast_run),
    "chords": ("Chord change", "Drawbar organ", chord_change),
}


def build():
    os.makedirs(BUILD, exist_ok=True)
    inc = os.path.join(CORE, "include")
    for src, out in ((os.path.join(HERE, "render.cpp"), "render"),
                     (os.path.join(CORE, "tests", "tools", "instrument_cpp.cpp"), "instrument_cpp")):
        subprocess.run(["g++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror", "-I", inc, src, "-o",
                        os.path.join(BUILD, out)], check=True)


def preset_code(name):
    return subprocess.run([os.path.join(BUILD, "instrument_cpp"), "--code", name], capture_output=True, text=True,
                          check=True).stdout.strip()


def script(code, notes, length):
    events = []
    for t, n, v, d in notes:
        events.append((t, [0x90, n, v]))
        events.append((t + d, [0x80, n, 0]))
    events.sort(key=lambda e: e[0])
    lines = [json.dumps(["make", RATE, BLOCK, code])]
    blocks, k = int(length * RATE / BLOCK), 0
    for b in range(blocks):
        top = (b + 1) * BLOCK / RATE
        while k < len(events) and events[k][0] < top:
            lines.append(json.dumps(["midi"] + events[k][1])); k += 1
        lines.append('["block",128]')
    return "\n".join(lines) + "\n"


def render(name, version, layout="round"):
    """Render one phrase one way; the prefix its files are under."""
    _, preset, make = PHRASES[name]
    code = CROSSED if preset is None else preset_code(preset)
    notes, length = make()
    path = os.path.join(BUILD, name + ".script")
    with open(path, "w") as f: f.write(script(code, notes, length))
    prefix = os.path.join(BUILD, "%s-%s%s" % (name, version, "" if layout == "round" else "-" + layout))
    args = [os.path.join(BUILD, "render"), path, prefix]
    dry = VERSIONS[version]
    args += ["trace"] if dry is None else ["paint", str(dry[0]), str(dry[1]), layout]
    subprocess.run(args, check=True)
    return prefix, length


def tables_of(prefix):
    rec = np.fromfile(prefix + ".tables", np.float32).reshape(-1, 3 + 512)
    return rec[:, 0].astype(int), rec[:, 1].astype(int), rec[:, 2], rec[:, 3:]


def powers(tabs):
    p = np.abs(np.fft.rfft(tabs, axis=1))[:, 1:65] ** 2
    return p / np.maximum(p.sum(axis=1, keepdims=True), 1e-12)


def measures(prefix):
    """The study's measures of Scan's tables: each table's harmonic centroid
    (a sine is 1), the share of its energy above the eighth harmonic and in
    the first; and how far each reading's table moves from one frame to the
    next (half the summed change of its normalised harmonic powers, nought
    still, one replaced), for the same note or hand from frame to frame."""
    frame, who, level, tabs = tables_of(prefix)
    if len(frame) == 0: return None
    pw = powers(tabs)
    cen = (pw * np.arange(1, 65)).sum(axis=1)
    move = []
    last = {}
    for i in range(len(frame)):
        k = who[i]
        if k in last and last[k][0] == frame[i] - 1:
            move.append(0.5 * np.abs(pw[i] - pw[last[k][1]]).sum())
        last[k] = (frame[i], i)
    move = np.array(move) if move else np.zeros(1)
    return dict(centroid=round(float(np.median(cen)), 2), centroid_p10=round(float(np.percentile(cen, 10)), 2),
                centroid_p90=round(float(np.percentile(cen, 90)), 2),
                high=round(float(np.median(pw[:, 8:].sum(axis=1))), 3), sine=round(float(np.median(pw[:, 0])), 3),
                movement=round(float(np.median(move)), 4), movement_p90=round(float(np.percentile(move, 90)), 4),
                readings=int(len(frame)))


def reads_of(prefix):
    rows = [list(map(float, l.split())) for l in open(prefix + ".reads") if l.strip()]
    return np.array(rows)


def picture(thick, wet, size=384):
    """The map as a plain picture: thickness in greys on white (a thick stroke
    black), wet paint in blue over it as far as it is wet and covering."""
    a = np.clip(thick / 1.2, 0, 1) ** 0.6
    cover = 1 - np.exp(-thick / 0.15)
    grey = 1 - 0.92 * a
    rgb = np.stack([grey, grey, grey], axis=-1)
    blue = np.array([0.20, 0.36, 0.78])
    w = np.clip(wet * cover, 0, 1)[..., None] * 0.85
    rgb = rgb * (1 - w) + blue * w * (0.55 + 0.45 * (1 - a[..., None]))
    img = Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8), "RGB")
    return img.resize((size, size), Image.NEAREST if size % N == 0 else Image.BILINEAR)


def maps_of(prefix):
    raw = np.fromfile(prefix + ".maps", np.float32).reshape(-1, 1 + 2 * N * N)
    return raw[:, 0], raw[:, 1:1 + N * N].reshape(-1, N, N), raw[:, 1 + N * N:].reshape(-1, N, N)


def mp3(prefix, out, length):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "f32le", "-ar", str(RATE), "-ac", "2", "-i",
                    prefix + ".f32", "-af", "afade=t=out:st=%g:d=0.3" % (length - 0.3), "-ar", "44100", "-b:a", "64k",
                    out], check=True)


def main(names):
    build()
    os.makedirs(os.path.join(HERE, "audio"), exist_ok=True)
    os.makedirs(os.path.join(HERE, "pictures"), exist_ok=True)
    path = os.path.join(HERE, "results.json")
    results = json.load(open(path)) if os.path.exists(path) else {}
    for name in names:
        out = {}
        for version in VERSIONS:
            prefix, length = render(name, version)
            m = measures(prefix)
            r = reads_of(prefix)
            spent, samples = map(float, open(prefix + ".cost").read().split())
            row = dict(scan=m, glow=round(float(np.median(r[:, 1])), 3), glow_p90=round(float(np.percentile(r[:, 1], 90)), 3),
                       motion=round(float(np.median(r[:, 2])), 3), motion_p90=round(float(np.percentile(r[:, 2], 90)), 3),
                       memory=round(float(np.median(r[:, 3])), 3), memory_p90=round(float(np.percentile(r[:, 3], 90)), 3),
                       realtime=round(spent / (samples / RATE), 4))
            if VERSIONS[version] is not None:
                landed = r[:, 9:12].sum(axis=0)
                total = max(landed.sum(), 1e-12)
                row.update(into_wet=round(float(landed[0] / total), 3), onto_dry=round(float(landed[1] / total), 3),
                           onto_bare=round(float(landed[2] / total), 3))
                times, thick, wet = maps_of(prefix)
                picture(thick[-1], wet[-1]).save(os.path.join(HERE, "pictures", "%s-%s.png" % (name, version)), optimize=True)
                picks = np.linspace(0, len(times) - 1, 8).round().astype(int)
                tiles = [picture(thick[i], wet[i], 128) for i in picks]
                strip = Image.new("RGB", (128 * 8 + 4 * 7, 128), (255, 255, 255))
                for k, im in enumerate(tiles): strip.paste(im, (k * 132, 0))
                strip.save(os.path.join(HERE, "pictures", "%s-%s-strip.png" % (name, version)), optimize=True)
                row["strip_times"] = [round(float(times[i]), 2) for i in picks]
            mp3(prefix, os.path.join(HERE, "audio", "%s-%s.mp3" % (name, version)), length)
            out[version] = row
            print(name, version, json.dumps(row))
        results[name] = out
    with open(path, "w") as f: json.dump(results, f, indent=1, sort_keys=True)


if __name__ == "__main__":
    main(sys.argv[1:] or list(PHRASES))
