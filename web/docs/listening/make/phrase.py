"""Render a phrase through render_cpp (or a scratch build of it): the heard pair as float32, and budget readings."""
import json, os, subprocess, struct, array
import measure
HERE = os.path.dirname(os.path.abspath(__file__))
RATE = 44100
END = 6.2
def notes_script(chord, over, chord_on=0.25, chord_off=5.0, over_len=0.6):
    ev = [(chord_on, 0x90, n, 100) for n in chord] + [(chord_off, 0x80, n, 0) for n in chord]
    for t, n in over: ev += [(t, 0x90, n, 96), (t + over_len, 0x80, n, 0)]
    return sorted(ev)
def render(setup, events, out_raw, exe=None, budget_every=None):
    exe = exe or os.path.join(HERE, "bin", "render_cpp")
    lines = [["make", RATE, measure.code(setup)], ["record", "heard", out_raw]]
    if budget_every: lines.append(["every", budget_every, "budget"])
    for t, a, b, c in events:
        lines += [["to", t], ["midi", a, b, c]]
    lines += [["to", END], ["record", "heard"]]
    p = out_raw + ".script"
    open(p, "w").write("\n".join(json.dumps(l) for l in lines) + "\n")
    return subprocess.run([exe, p], check=True, capture_output=True, text=True).stdout
def stereo(raw):
    a = array.array("f"); a.frombytes(open(raw, "rb").read()); return a[0::2], a[1::2]
def wav(path, chans):
    n = len(chans[0]); fade = int(0.05 * RATE)
    data = bytearray()
    for i in range(n):
        g = min(1.0, (n - 1 - i) / fade)
        for c in chans:
            v = max(-1.0, min(1.0, c[i] * g)); data += struct.pack("<h", int(round(v * 32767)))
    nc = len(chans)
    hdr = b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt " + struct.pack("<IHHIIHH", 16, 1, nc, RATE, RATE * 2 * nc, 2 * nc, 16) \
        + b"data" + struct.pack("<I", len(data))
    open(path, "wb").write(hdr + bytes(data))
