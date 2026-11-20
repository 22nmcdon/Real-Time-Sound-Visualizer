"""The controllers on the brush (painting, step 3): five short phrases, each
played with a controller moving and painted twice by the core - once with the
brush hearing the controller, and once deaf to it - so the two differ only in
what the brush did, and what Scan then read off the paint.

The owner's table (16 Nov) and what each phrase plays:

  pedal    the sustain pedal: a pluck's slow melody under it. The brush stays
           on the canvas through the silences and the paint stays wet.
  wheel    the mod wheel: a pad's chord held while the wheel goes to the top,
           down to the bottom and back to its middle. The brush's load and
           pressure, dry and scratchy at the bottom, heavy at the top. The
           wheel is also Expression's vibrato, as it is by default, in both.
  bend     the pitch wheel, its range an octave (two semitones is under a
           cell on the round layout, which the eye cannot find under a
           stroke ten cells wide): a fifth held and bent up an octave, back,
           down one and back. The stroke bends with the pitch; deaf, it stays on
           the note's ring while the sound bends.
  strikes  velocity: a melody alternating soft (30) and hard (127) strikes at
           Strike 100. Spatter, more and further the harder; without it, none.
  lean     aftertouch: a chord held and leaned on, then let off. The stroke
           widens and presses in.

For each phrase and way (`with`, `without`) this writes, beside itself:

  audio/NAME-WAY.mp3            what the core plays
  pictures/NAME-WAY-map.png     the map at the phrase's end (thickness grey, wet blue)
  pictures/NAME-WAY-look.jpg    the live look at the end: the page's own paintView in
                                headless Chromium's WebGL 2, fed the core's stamps a
                                sixtieth of a second at a time (paint-width's Looks)
  results.json                  Scan's measures, the Picture amount's reads, the brush's
                                median width, the paint laid and how wet it is at the end

    CHROME=/opt/pw-browsers/chromium python3 web/docs/listening/paint-controllers/render.py [NAME ...]
"""
import importlib.util, json, os, subprocess, sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
CORE = os.path.join(ROOT, "core")
BUILD = os.path.join(CORE, "build", "listening", "paint-controllers")
N = 128

_spec = importlib.util.spec_from_file_location("paintwidth", os.path.join(HERE, "..", "paint-width", "render.py"))
pw = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pw)
step1 = pw.step1

ALL, PEDAL, WHEEL, BEND, PRESSURE = 15, 1, 2, 4, 8

PLUCK = pw.PLUCK
PAD = {"shape": "ramp", "midiMode": "poly", "oscScan": 60, "pictureAmount": 0, "atk": 200, "dec": 800, "sus": 80, "rel": 1500}
TONE = {"shape": "sine", "midiMode": "poly", "oscScan": 60, "pictureAmount": 0, "atk": 5, "dec": 1000, "sus": 60, "rel": 600}
STRUCK = {"shape": "sine", "midiMode": "poly", "oscScan": 60, "pictureAmount": 0, "scanStrike": 100, "atk": 1, "dec": 600,
          "sus": 30, "rel": 400}


def ramp(t0, t1, v0, v1, make, every=0.04):
    """A controller moved from v0 to v1 (nought to one) between t0 and t1, a message every 40 ms, as a hand sends them."""
    out, k = [], 0
    steps = max(1, int(round((t1 - t0) / every)))
    for k in range(steps + 1):
        f = k / steps
        out.append((t0 + (t1 - t0) * f, make(v0 + (v1 - v0) * f)))
    return out


def cc(number):
    return lambda v: [0xB0, number, int(round(127 * v))]


def bend(v):
    # -1 to 1, as the wheel's fourteen bits.
    raw = 8192 + int(round(v * (8191 if v >= 0 else 8192)))
    raw = max(0, min(16383, raw))
    return [0xE0, raw & 127, raw >> 7]


def pressure(v):
    return [0xD0, int(round(127 * v))]


def pedal():
    notes, length = pw.slow_melody()
    return notes, [(0.05, [0xB0, 64, 127]), (length - 0.6, [0xB0, 64, 0])], length


def wheel():
    notes = [(0.2, n, 90, 8.0) for n in (48, 55, 64)]
    ev = ramp(0.5, 3.0, 0, 1, cc(1)) + ramp(3.0, 5.5, 1, 0, cc(1)) + ramp(5.5, 7.5, 0, 0.5, cc(1))
    return notes, ev, 9.5


def bent():
    notes = [(0.2, 57, 90, 7.0), (0.2, 64, 90, 7.0)]
    ev = ramp(1.0, 2.5, 0, 1, bend) + ramp(3.5, 5.0, 1, 0, bend) + ramp(5.0, 6.0, 0, -1, bend) + ramp(6.0, 6.8, -1, 0, bend)
    return notes, ev, 8.0


def strikes():
    notes = [(0.3 + 0.6 * k, n, 30 if k % 2 == 0 else 127, 0.5) for k, n in enumerate((60, 62, 64, 65, 67, 65, 64, 62))]
    return notes, [], 6.0


def lean():
    notes = [(0.2, n, 90, 6.0) for n in (57, 64, 69)]
    ev = ramp(1.5, 2.5, 0, 1, pressure) + ramp(4.0, 5.0, 1, 0, pressure)
    return notes, ev, 7.5


# Each phrase: its title, its setup, how it goes, and the brush without it - what it is deaf to, and the spatter.
PHRASES = {
    "pedal": ("A pluck's slow melody under the pedal", PLUCK, pedal, (ALL - PEDAL, -1)),
    "wheel": ("A held chord with the mod wheel swept", PAD, wheel, (ALL - WHEEL, -1)),
    "bend": ("A bend", dict(TONE, bendRange=12), bent, (ALL - BEND, -1)),
    "strikes": ("Soft against hard strikes", STRUCK, strikes, (ALL, 0)),
    "lean": ("Aftertouch leaned on", PAD, lean, (ALL - PRESSURE, -1)),
}


def script(code, notes, events, length):
    ev = []
    for t, n, v, d in notes:
        ev.append((t, [0x90, n, v])); ev.append((t + d, [0x80, n, 0]))
    ev += events
    ev.sort(key=lambda e: e[0])
    lines = [json.dumps(["make", step1.RATE, step1.BLOCK, code])]
    blocks, k = int(length * step1.RATE / step1.BLOCK), 0
    for b in range(blocks):
        top = (b + 1) * step1.BLOCK / step1.RATE
        while k < len(ev) and ev[k][0] < top:
            lines.append(json.dumps(["midi"] + ev[k][1])); k += 1
        lines.append('["block",128]')
    return "\n".join(lines) + "\n"


def build():
    os.makedirs(BUILD, exist_ok=True)
    subprocess.run(["g++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror", "-I", os.path.join(CORE, "include"),
                    os.path.join(HERE, "render.cpp"), "-o", os.path.join(BUILD, "render")], check=True)


def render(name, way):
    _, setup, make, (deaf, spatter) = PHRASES[name]
    notes, events, length = make()
    path = os.path.join(BUILD, name + ".script")
    with open(path, "w") as f: f.write(script(json.dumps(setup), notes, events, length))
    prefix = os.path.join(BUILD, "%s-%s" % (name, way))
    hears, at = (ALL, -1) if way == "with" else (deaf, spatter)
    subprocess.run([os.path.join(BUILD, "render"), path, prefix, "2", str(hears), str(at)], check=True)
    return prefix, length


def main(names):
    build()
    for d in ("audio", "pictures"): os.makedirs(os.path.join(HERE, d), exist_ok=True)
    path = os.path.join(HERE, "results.json")
    results = json.load(open(path)) if os.path.exists(path) else {}
    looks = pw.Looks()
    try:
        for name in PHRASES:
            if name not in names: continue
            for way in ("with", "without"):
                prefix, length = render(name, way)
                m = step1.measures(prefix)
                r = step1.reads_of(prefix)
                _, thick, wet = step1.maps_of(prefix)
                _, S = pw.stamps_of(prefix)
                laid = float(thick[-1].sum())
                row = dict(scan=m, glow=round(float(np.median(r[:, 1])), 3), motion=round(float(np.median(r[:, 2])), 3),
                           memory=round(float(np.median(r[:, 3])), 3),
                           brush_cells=round(float(np.median(S[:, 4]) * N), 2) if len(S) else 0,
                           brush_p90=round(float(np.percentile(S[:, 4], 90) * N), 2) if len(S) else 0,
                           paint=round(laid, 1), wet=round(float((thick[-1] * wet[-1]).sum() / max(laid, 1e-9)), 2),
                           stamps=int(len(S)))
                step1.picture(thick[-1], wet[-1]).save(os.path.join(HERE, "pictures", "%s-%s-map.png" % (name, way)), optimize=True)
                looks.look(prefix, os.path.join(HERE, "pictures", "%s-%s-look.jpg" % (name, way)))
                step1.mp3(prefix, os.path.join(HERE, "audio", "%s-%s.mp3" % (name, way)), length)
                results.setdefault(name, {})[way] = row
                print(name, way, json.dumps(row), flush=True)
                with open(path, "w") as f: json.dump(results, f, indent=1, sort_keys=True)
    finally:
        looks.close()


if __name__ == "__main__":
    main(sys.argv[1:] or list(PHRASES))
