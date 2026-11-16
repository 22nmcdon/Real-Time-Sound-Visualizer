"""Render the owner's sequence through render_cpp (or a scratch build) and read it."""
import json, os, subprocess, sys, base64, re
import numpy as np
REPO = "/home/user/Real-Time-Sound-Visualizer"
HERE = os.path.dirname(os.path.abspath(__file__))
RATE = 44100
V = int(re.search(r"kSetupVersion = (\d+)", open(REPO + "/core/include/scope/setup.h").read()).group(1))
def code(fields):
    return base64.b64encode(json.dumps(dict({"v": V}, **fields)).encode()).decode().rstrip("=")
HT = {"timebase": 3, "pictureAmount": 96, "pictureSwell": True}   # Harmonic tone, as the bank has it
# The owner's sequence: a bass note alone, a higher note added, back to the bass alone, let go.
T_BASS, T_UP, T_UPOFF, T_BASSOFF, END = 0.2, 1.8, 3.4, 5.2, 6.0
BASS, UP = 36, 64
def seq(bass=BASS, up=UP, vel=100):
    return [(T_BASS, 0x90, bass, vel), (T_UP, 0x90, up, vel), (T_UPOFF, 0x80, up, 0), (T_BASSOFF, 0x80, bass, 0)]
def render(fields, name, events=None, exe=None, every=0.01, reads=("limiter", "loop", "sources", "reads", "table"), end=END, rate=RATE):
    exe = exe or os.path.join(HERE, "..", "bin", "render_cpp")
    raw = os.path.join(HERE, "out", name + ".f32"); os.makedirs(os.path.dirname(raw), exist_ok=True)
    lines = [["make", rate, code(fields)], ["record", "heard", raw]]
    if every: lines.append(["every", every] + list(reads))
    for t, a, b, c in (events if events is not None else seq()):
        lines += [["to", t], ["midi", a, b, c]]
    lines += [["to", end], ["record", "heard"]]
    p = raw + ".script"
    open(p, "w").write("\n".join(json.dumps(l) for l in lines) + "\n")
    out = subprocess.run([exe, p], check=True, capture_output=True, text=True).stdout
    a = np.fromfile(raw, dtype="<f4").astype(float)
    return a[0::2], a[1::2], out
def readings(out):
    """{name: [(t, [fields...])]}"""
    rows = {}; t = None
    for line in out.splitlines():
        w = line.split()
        if not w: continue
        if w[0] == "at": t = float(w[1]); continue
        rows.setdefault(w[0], []).append((t, w[1:]))
    return rows
