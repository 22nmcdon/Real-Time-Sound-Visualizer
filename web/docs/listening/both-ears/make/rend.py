"""Render a phrase through a render_cpp build: the heard pair, the drawn lanes, the grid, and the readings."""
import json, os, subprocess, base64, re
import numpy as np
REPO = "/home/user/Real-Time-Sound-Visualizer"
HERE = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
OUTD = os.path.join(os.path.dirname(HERE), "out")
RATE = 44100
LANES = 6   # kRingLanes
V = int(re.search(r"kSetupVersion = (\d+)", open(REPO + "/core/include/scope/setup.h").read()).group(1))
def code(fields):
    return base64.b64encode(json.dumps(dict({"v": V}, **fields)).encode()).decode().rstrip("=")
HT = {"timebase": 3, "pictureAmount": 96, "pictureSwell": True}   # Harmonic tone, as the bank has it
# The owner's sequence: C2 alone, E4 added, C2 alone again, let go (the one-to-two page's).
T_BASS, T_UP, T_UPOFF, T_BASSOFF, END = 0.2, 1.8, 3.4, 5.2, 6.0
OWNER = [(T_BASS, 0x90, 36, 100), (T_UP, 0x90, 64, 100), (T_UPOFF, 0x80, 64, 0), (T_BASSOFF, 0x80, 36, 0)]
# The chord: C3, then E3, G3, C4 added one at a time, released from the top one at a time.
CHORD_NOTES = [48, 52, 55, 60]
CHORD_ON = [0.2, 1.1, 2.0, 2.9]
CHORD_OFF = {60: 3.8, 55: 4.7, 52: 5.6, 48: 6.5}   # let go from the top, C3 last
CHORD_END = 7.3
CHORD = sorted([(t, 0x90, n, 100) for t, n in zip(CHORD_ON, CHORD_NOTES)] + [(CHORD_OFF[n], 0x80, n, 0) for n in CHORD_NOTES])
READS = ("table", "sources", "reads", "loop", "scan", "stage", "lmeter", "eye", "meter", "gridstat", "layers", "griddump", "limiter")
def render(exe, fields, events, end, name, every=0.01, reads=READS, rate=RATE, full=True, limiter=True):
    os.makedirs(OUTD, exist_ok=True)
    base = os.path.join(OUTD, name)
    lines = [["make", rate, code(fields)], ["record", "heard", base + ".heard"]]
    if not limiter: lines.append(["control", "limiter", "0"])
    if full: lines += [["record", "lanes", base + ".lanes"], ["record", "grid", base + ".grid"]]
    if every: lines.append(["every", every] + [r for r in reads if full or r not in ("griddump",)])
    for t, a, b, c in events:
        lines += [["to", t], ["midi", a, b, c]]
    lines += [["to", end], ["record", "heard"]]
    if full: lines += [["record", "lanes"], ["record", "grid"]]
    p = base + ".script"
    open(p, "w").write("\n".join(json.dumps(l) for l in lines) + "\n")
    out = subprocess.run([os.path.join(BIN, exe), p], check=True, capture_output=True, text=True).stdout
    a = np.fromfile(base + ".heard", dtype="<f4").astype(float)
    r = {"L": a[0::2], "R": a[1::2], "out": out, "base": base}
    if full:
        ln = np.fromfile(base + ".lanes", dtype="<f4").astype(float)
        r["X"], r["Y"] = ln[0::LANES], ln[1::LANES]
    return r
def readings(out):
    rows = {}; t = None
    for line in out.splitlines():
        w = line.split()
        if not w: continue
        if w[0] == "at": t = float(w[1]); continue
        rows.setdefault(w[0], []).append((t, w[1:]))
    return rows
