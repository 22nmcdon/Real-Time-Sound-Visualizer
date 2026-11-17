"""Off means off, rendered both ways (the picture reach audit, Part A).

Today a rack module's switch takes its Mix to nought (the Plane: its shaping
and turn to rest), and the Picture amount's fixed pushes (kStageBundles in
core/include/scope/matrix.h) are added on top of the knob, so a switched-off
delay, phaser or Plane twist is brought back in from nought by the picture.
This renders every bank preset under Settled and Breathing twice from the
core's offline renderer - as the instrument plays today, and with
render_cpp's `offmeansoff`, which ignores the Picture's push onto a module
switched off and so does not run it - and writes:

  wav/<slug>-today.wav, wav/<slug>-off.wav   the same performance: a chord held
                                            six seconds, then a moving phrase
  fig/<slug>-today.png, fig/<slug>-off.png  the 64 by 64 grid Scan reads, at
                                            the end of the held chord
  results.json                              the measured line per pair

and index.html reads results.json for its lines. Every preset is rendered at
its own Picture amount with the delay, phaser and Plane as it ships them,
which is off in every one; Harmonic tone again at Amount 100.

The WAVs are 22.05 kHz 16-bit stereo, decimated from the 44.1 kHz render by
a windowed-sinc low-pass, to keep them small; a pair the two ways render the
same to the bit is written once. The measures are on the 44.1 kHz render.

The heading measure is honestytest.py's, ported here sample for sample: one
probe a hand (the preset's own probe), held ten seconds and let go for four
and a half, the left channel's movement between two 4096-sample windows a
quarter second apart, every quarter second of audio. honestytest reads the
picture's left lane in the browser; this reads the heard left channel from
the core, which is the same sound since 16 Nov unless the Width is drawn too
(no bank preset draws it). Its verdict on the default render is the check
on the port: each preset must measure under its own heading today.

    python3 web/docs/listening/off-means-off/render.py
"""
import json, math, os, struct, subprocess, sys, wave, zlib
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
CORE = os.path.join(ROOT, "core")
BUILD = os.path.join(CORE, "build", "audit")
WORK = os.path.join(BUILD, "off-means-off")
RATE = 44100


def tool(name):
    os.makedirs(BUILD, exist_ok=True)
    exe = os.path.join(BUILD, name)
    subprocess.run(["g++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror", "-I", os.path.join(CORE, "include"),
                    os.path.join(CORE, "tests", "tools", name + ".cpp"), "-o", exe], check=True)
    return exe


def render(exe, lines, tag):
    os.makedirs(WORK, exist_ok=True)
    path = os.path.join(WORK, tag + ".txt")
    with open(path, "w") as f: f.write("\n".join(json.dumps(l) for l in lines) + "\n")
    out = subprocess.run([exe, path], check=True, capture_output=True, text=True).stdout
    if "\nno " in "\n" + out: raise RuntimeError(out)
    return out


def heard(path):
    a = np.fromfile(path, dtype="<f4")
    return a.reshape(-1, 2).astype(np.float64)


# --- the performance -------------------------------------------------------------------

def chord(setup):
    return [36, 43, 64, 67] if setup.get("layers") == "split" else [48, 55, 60, 64]

MELODY = [72, 71, 67, 69, 64, 67, 62, 64, 60, 62, 64, 67, 69, 72, 76]
BASS = [36, 41, 43, 36]

def performance(setup):
    """MIDI as (seconds, bytes): the chord held six seconds, then a phrase of
    eighths at 120, and under it a bass a bar in a split."""
    ev = [(0.0, [0x90, n, 100]) for n in chord(setup)] + [(6.0, [0x80, n, 0]) for n in chord(setup)]
    for k, n in enumerate(MELODY):
        t = 6.25 + 0.25 * k
        ev += [(t, [0x90, n, 96]), (t + 0.22, [0x80, n, 0])]
    if setup.get("layers") == "split":
        for k, n in enumerate(BASS):
            ev += [(6.25 + k, [0x90, n, 90]), (6.25 + k + 0.9, [0x80, n, 0])]
    return sorted(ev, key=lambda e: e[0])

END = 11.0

def script(code, patch, off, events, end, heard_to=None, reads=(), grid_at=None, grid_to=None, every=None):
    lines = [["make", RATE, code, patch or {}]]
    if off: lines.append(["offmeansoff", True])
    if heard_to: lines.append(["record", "heard", heard_to])
    if grid_to: lines.append(["record", "grid", grid_to])
    if every: lines.append(["every", every[0], *every[1]])
    marks = sorted(set([t for t, _ in events] + ([grid_at] if grid_at else []) + [end]))
    for t in marks:
        lines.append(["to", t])
        for et, b in events:
            if et == t: lines.append(["midi", *b])
        if grid_at == t: lines.append(["read", "griddump"])
    return lines


# --- honestytest's measure, ported ---------------------------------------------------------

def bands(x):
    n = len(x)
    w = x * (0.5 - 0.5 * np.cos(2 * np.pi * np.arange(n) / (n - 1)))
    spec = np.fft.rfft(w)
    p = (spec.real ** 2 + spec.imag ** 2)[1:n // 2]
    f = np.arange(1, n // 2) * 44100 / n
    keep = f >= 40
    idx = np.minimum(47, np.floor(np.log2(f[keep] / 40) * 5)).astype(int)
    b = np.zeros(48)
    np.add.at(b, idx, p[keep])
    tot = b.sum()
    return np.sqrt(b / tot) if tot > 0 else b

HOLD, AFTER = 10.0, 4.5

def honesty(left):
    """honestytest's readings on a left channel rendered from the key down."""
    N, GAP = 4096, round(RATE / 4)
    out, first = [], True
    t = 0.25
    while t <= HOLD + AFTER + 1e-9:
        end = int(round(t * RATE))
        start = end - (N + GAP)
        if start >= 0:
            l = left[start:end]
            rms = math.sqrt(float(np.mean(l[GAP:GAP + N] ** 2)))
            move = 0.0
            if not first:
                move = float(np.sqrt(np.sum((bands(l[GAP:GAP + N]) - bands(l[:N])) ** 2)))
            first = False
            out.append({"t": t, "phase": "held" if t <= HOLD else "after", "move": move, "rms": rms})
        t += 0.25
    mean = lambda xs: sum(xs) / len(xs) if xs else 0.0
    held = [s for s in out if s["phase"] == "held"]
    after = [s for s in out if s["phase"] == "after" and s["t"] >= HOLD + 2.5]
    return {"early": mean([s["move"] for s in held if 0.3 <= s["t"] < 2.0]),
            "late": mean([s["move"] for s in held if s["t"] >= HOLD - 3.0]),
            "most": max([s["move"] for s in held if s["t"] >= 0.5] or [0.0]),
            "afterRms": mean([s["rms"] for s in after])}

RULES = {
    "Still": lambda m: m["most"] < 0.005,
    "Settled": lambda m: m["early"] >= 0.008 and m["late"] <= 0.015 and m["late"] <= m["early"] / 2,
    "Breathing": lambda m: m["late"] >= 0.02 and m["afterRms"] < 0.005,
}

def probes(name, setup):
    if name == "Crossed hands": return [[48, 67]]
    if name == "Turning fifths": return [[48, 55]]
    if setup.get("layers") == "split": return [[36], [67]]
    return [[60]]


# --- the files ------------------------------------------------------------------------------

def decimate(x):
    """44.1 kHz to 22.05: a 127-tap windowed-sinc low-pass at 10 kHz, every second sample."""
    taps = 127
    k = np.arange(taps) - (taps - 1) / 2
    fc = 10000 / RATE
    h = 2 * fc * np.sinc(2 * fc * k) * np.blackman(taps)
    h /= h.sum()
    return np.stack([np.convolve(x[:, c], h, mode="same")[::2] for c in range(2)], axis=1)

def write_wav(path, x):
    y = np.clip(np.round(decimate(x) * 32767), -32768, 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(RATE // 2)
        w.writeframes(y.tobytes())

def write_png(path, grid, top):
    """The grid as Scan reads it, 64 by 64, each cell 4 by 4 pixels, by the
    square root of its share of `top` (the pair's brightest), in the trace's green."""
    n, s = 64, 4
    g = np.sqrt(np.clip(grid.reshape(n, n) / top if top > 0 else grid.reshape(n, n) * 0, 0, 1))
    rows = []
    for y in range(n):   # the grid's first row is the screen's top
        line = bytearray()
        for x in range(n):
            v = g[y, x]
            line += bytes((int(18 + 60 * v), int(20 + 225 * v), int(18 + 120 * v))) * s
        rows += [b"\x00" + bytes(line)] * s
    raw = b"".join(rows)
    def chunk(kind, data): return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", n * s, n * s, 8, 2, 0, 0, 0)) \
        + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    with open(path, "wb") as f: f.write(png)

def spectral_distance(x, y, n=4096):
    """The mean distance between the two's band shares, window for window (honestytest's bands)."""
    ds = [float(np.sqrt(np.sum((bands(x[i:i + n]) - bands(y[i:i + n])) ** 2))) for i in range(0, len(x) - n + 1, n // 2)]
    return sum(ds) / len(ds) if ds else 0.0


def slug(name, extra=""):
    return (name.lower().replace(" ", "-") + extra)


def db(x):
    return -math.inf if x <= 0 else 20 * math.log10(x)


def main():
    render_exe, inst_exe = tool("render_cpp"), tool("instrument_cpp")
    library = json.loads(subprocess.run([sys.executable, "-c", PRESETS], check=True, capture_output=True, text=True).stdout)
    for d in ("wav", "fig"): os.makedirs(os.path.join(HERE, d), exist_ok=True)
    runs = [(h, n, s, None) for h, entries in library for n, s in entries]
    runs.append(("Breathing", "Harmonic tone", dict(library[1][1][0][1]), 100))
    results = []
    for heading, name, setup, amount in runs:
        code = subprocess.run([inst_exe, "--code", name], check=True, capture_output=True, text=True).stdout.strip()
        patch = {"pictureAmount": amount} if amount is not None else {}
        tag = slug(name, "-at-%d" % amount if amount is not None else "")
        ev = performance(setup)
        sounds, grids, routes = {}, {}, {}
        for way, off in (("today", False), ("off", True)):
            wav_raw = os.path.join(WORK, tag + "-" + way + ".f32")
            grid_raw = os.path.join(WORK, tag + "-" + way + ".grid")
            out = render(render_exe, script(code, patch, off, ev, END, heard_to=wav_raw, grid_at=5.9, grid_to=grid_raw,
                                            every=(0.1, ["loop"])), tag + "-" + way)
            sounds[way] = heard(wav_raw)
            grids[way] = np.fromfile(grid_raw, dtype="<f4")
            # The loop's held value into the delay, the twist and the phaser, read every tenth of a second.
            got = {"echo": [], "twist": [], "phaser": []}
            for line in out.split("\n"):
                w = line.split()
                if not w or w[0] != "loop": continue
                held = {int(p.split(":")[0]): float(p.split(":")[1]) for p in w[1:] if ":" in p}
                for k, s in (("echo", 24), ("twist", 18), ("phaser", 35)): got[k].append(abs(held.get(s, 0.0)))
            routes[way] = {k: (max(v) if v else 0.0, sum(v) / len(v) if v else 0.0) for k, v in got.items()}
        a, b = sounds["today"], sounds["off"]
        same = bool(np.array_equal(a, b))
        rms = lambda x: math.sqrt(float(np.mean(x ** 2))) if len(x) else 0.0
        held_part, phrase_part = slice(int(0.5 * RATE), int(6.0 * RATE)), slice(int(6.25 * RATE), int(10.0 * RATE))
        parts = (("held", held_part), ("phrase", phrase_part))
        # The difference against the sound, which past 0 dB says the two have
        # drifted apart in phase more than they differ in kind; so also the
        # level each way, and the spectrum's distance - honestytest's bands,
        # window against window at the same moment, a mean over the part.
        diff = {part: db(rms(a[sl] - b[sl]) / rms(a[sl])) if rms(a[sl]) > 0 else -math.inf for part, sl in parts}
        level = {part: db(rms(b[sl]) / rms(a[sl])) if rms(a[sl]) > 0 and rms(b[sl]) > 0 else 0.0 for part, sl in parts}
        spectral = {part: spectral_distance(a[sl, 0], b[sl, 0]) for part, sl in parts}
        # Mono-compatible: what the pair loses folded to one channel, against each channel's own level.
        mono = {way: db(rms((x[:, 0] + x[:, 1]) / 2) / math.sqrt((rms(x[:, 0]) ** 2 + rms(x[:, 1]) ** 2) / 2))
                for way, x in (("today", a), ("off", b))}
        top = float(max(grids["today"].max(), grids["off"].max()))
        write_png(os.path.join(HERE, "fig", tag + "-today.png"), grids["today"], top)
        write_png(os.path.join(HERE, "fig", tag + "-off.png"), grids["off"], top)
        write_wav(os.path.join(HERE, "wav", tag + "-today.wav"), a)
        if not same: write_wav(os.path.join(HERE, "wav", tag + "-off.wav"), b)
        elif os.path.exists(os.path.join(HERE, "wav", tag + "-off.wav")): os.remove(os.path.join(HERE, "wav", tag + "-off.wav"))
        # The heading, both ways, on the preset's own probes.
        verdicts = {}
        for way, off in (("today", False), ("off", True)):
            per = []
            for notes in probes(name, setup):
                ev2 = [(0.0, [0x90, n, 100]) for n in notes] + [(HOLD, [0x80, n, 0]) for n in notes]
                raw = os.path.join(WORK, tag + "-" + way + "-probe.f32")
                render(render_exe, script(code, patch, off, ev2, HOLD + AFTER, heard_to=raw), tag + "-" + way + "-probe")
                m = honesty(heard(raw)[:, 0])
                per.append({"notes": notes, **m, "under": [h for h, r in RULES.items() if r(m)]})
            verdicts[way] = per
        r = {"heading": heading, "name": name, "tag": tag, "amount": amount if amount is not None else setup.get("pictureAmount"),
             "same": same, "diff": diff, "level": level, "spectral": spectral, "mono": mono, "routes": routes, "verdicts": verdicts}
        results.append(r)
        print("%-10s %-28s same=%s held %.1f dB phrase %.1f dB lvl %.1f/%.1f spec %.3f/%.3f | echo %.3f twist %.3f phaser %.3f | today %s off %s" % (
            heading, tag, same, diff["held"], diff["phrase"], level["held"], level["phrase"], spectral["held"], spectral["phrase"], routes["today"]["echo"][0], routes["today"]["twist"][0],
            routes["today"]["phaser"][0],
            "/".join(",".join(p["under"]) or "none" for p in verdicts["today"]),
            "/".join(",".join(p["under"]) or "none" for p in verdicts["off"])))
    with open(os.path.join(HERE, "results.json"), "w") as f:
        json.dump(results, f, indent=1, default=lambda v: None if isinstance(v, float) and not math.isfinite(v) else v)
    # The port of the measure is believed only if today's render of every
    # preset measures under its own heading, as honestytest requires of the page.
    wrong = [(r["tag"], p["notes"], p["under"]) for r in results if r["amount"] == r.get("amount")
             for p in r["verdicts"]["today"] if r["heading"] not in p["under"] and "-at-" not in r["tag"]]
    print("today's renders under their own heading:", "all" if not wrong else wrong)


# The bank as presets.h has it: its pieces joined, the page's JSON.
PRESETS = r"""
import json, re, os
s = open(os.path.join(%r, 'include', 'scope', 'presets.h')).read()
lib = json.loads(''.join(re.findall(r'R"preset\((.*?)\)preset"', s, re.S)))
print(json.dumps([[sec[0], [[e[0], e[1]] for e in sec[1]]] for sec in lib]))
""" % CORE

if __name__ == "__main__":
    main()
