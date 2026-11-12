"""The study's four phrases, played offline through the instrument's own core.

Each phrase is a setup code (a bank preset's, or the owner's own for Crossed
hands) and a timed list of notes. `render.cpp` - a copy of
core/tests/tools/instrument_cpp.cpp's loop that writes files - plays the
script a 128-frame block at a time, a note landing at the top of the block it
falls in (2.7 ms at 48 kHz, as the plugin's host would deliver it), and writes
the heard pair and a log of the core's voices. Out, in ../build/: NAME.f32,
NAME.voices.txt and NAME.notes.json (the sequence, so the painting knows which
key was struck how hard); in ../audio/: NAME.mp3 at 96 kbps for the page.

    python3 phrases.py            # build render.cpp, play all four
"""
import json, os, random, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
STUDY = os.path.dirname(HERE)
BUILD = os.path.join(STUDY, "build")
AUDIO = os.path.join(STUDY, "audio")
RATE, BLOCK = 48000, 128

# The owner's repeatable Crossed hands (the-picture-amount.md): Crossed hands
# at Picture 47, delay 35 (feedback 47), phaser 30, reverb 26, split at C4.
CROSSED = ("eyJ2IjoxMCwic2hhcGUiOiJzaW5lIiwib3NjU2NhbiI6MTAwLCJzY2FuUmVhZHNBIjoiQiIsInNjYW5SZWFkc0IiOiJBIiwiZnJlcSI6MTEwLCJjeWNsZXMiOiIiLCJkaXNwbGF5IjoieHkiLCJwZXJzaXN0ZW5jZSI6IjAuMDI1NSIsIm1pZGlNb2RlIjoicG9seSIsInBvbHlSb3VuZCI6dHJ1ZSwibGF5ZXJzIjoic3BsaXQiLCJwaWN0dXJlQW1vdW50Ijo0NywiZGVsYXlNaXgiOjM1LCJkZWxheUZlZWRiYWNrIjo0NywicGhhc2VyTWl4IjozMCwicmV2ZXJiTWl4IjoyNn0")


def preset_code(name):
    tool = os.path.join(BUILD, "instrument_cpp")
    return subprocess.run([tool, "--code", name], capture_output=True, text=True, check=True).stdout.strip()


def held_pad():
    # A Cmaj9 voicing held nine seconds, then its 1.5 s release rung out.
    return [(0.25, n, 80, 9.0) for n in (48, 55, 62, 64, 71)], 12.0


def crossed_hands():
    # The owner's sequence, compressed from 27 s to 15 so it fits the study's
    # 8 to 20: every gesture kept and in its order, the gaps shortened.
    notes = [(0.3, n, 70, 3.7) for n in (37, 44, 48)]          # Db2 Ab2 C3
    notes += [(4.0, n, 70, 9.0) for n in (42, 49, 53)]         # Gb2 Db3 F3, changed mid-run
    scale = [61, 63, 65, 68, 70, 72, 73, 75, 77]               # Db major pentatonic with C, Db4 to F5
    run = scale + scale[-2:0:-1]
    t, i = 1.0, 0
    while t < 6.0:
        fast = t >= 2.6
        step = 1 / 8 if fast else 1 / 5
        notes.append((t, run[i % len(run)], 95 if fast else 55, step * 0.9))
        t += step; i += 1
    notes += [(8.0, 70, 40, 0.07), (8.07, 72, 40, 1.0)]       # Bb4 grace into C5
    notes += [(9.6, 66, 40, 0.07), (9.67, 68, 40, 2.6)]        # Gb4 grace into Ab4, held
    return notes, 15.5


def fast_run():
    # C major from C4 to C5 and back, three times at nine notes a second,
    # a crescendo to the top of each pass and back, with a little scatter.
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
    # ii-V-I-vi in C, four-note voicings, two and a half seconds each.
    chords = [(50, 53, 57, 60), (43, 53, 59, 62), (48, 52, 55, 59), (45, 52, 55, 60)]
    notes = []
    for k, ch in enumerate(chords):
        for n in ch: notes.append((0.3 + 2.5 * k, n, 78, 2.4))
    return notes, 11.6


PHRASES = {
    "pad": ("Slow pad", held_pad),
    "crossed": (None, crossed_hands),
    "run": ("Tine piano", fast_run),
    "chords": ("Drawbar organ", chord_change),
}


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


def main(names):
    os.makedirs(BUILD, exist_ok=True); os.makedirs(AUDIO, exist_ok=True)
    inc = os.path.join(ROOT, "core", "include")
    for src, out in (("render.cpp", "render"), ("scanread.cpp", "scanread"),
                     (os.path.join(ROOT, "core/tests/tools/instrument_cpp.cpp"), "instrument_cpp")):
        subprocess.run(["g++", "-std=c++17", "-O2", "-I", inc, os.path.join(HERE, src), "-o", os.path.join(BUILD, out)], check=True)
    for name in names:
        preset, make = PHRASES[name]
        code = CROSSED if preset is None else preset_code(preset)
        notes, length = make()
        path = os.path.join(BUILD, name)
        with open(path + ".script", "w") as f: f.write(script(code, notes, length))
        with open(path + ".notes.json", "w") as f:
            json.dump({"preset": preset or "Crossed hands (the owner's)", "code": code, "rate": RATE, "length": length,
                       "split": 60 if preset is None else None,
                       "notes": [{"t": t, "note": n, "vel": v, "dur": d} for t, n, v, d in notes]}, f)
        subprocess.run([os.path.join(BUILD, "render"), path + ".script", path + ".f32", path + ".voices.txt"], check=True)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "f32le", "-ar", str(RATE), "-ac", "2", "-i", path + ".f32",
                        "-af", "afade=t=out:st=%g:d=0.3" % (length - 0.3), "-b:a", "96k", os.path.join(AUDIO, name + ".mp3")], check=True)
        print(name, "rendered", round(length, 1), "s")


if __name__ == "__main__":
    main(sys.argv[1:] or list(PHRASES))
