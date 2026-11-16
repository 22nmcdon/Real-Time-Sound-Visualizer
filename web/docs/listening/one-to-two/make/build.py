"""Every take and number on the one-to-two listening page."""
import base64, json, os, struct
import numpy as np
import rend, meas, summ
B = "/tmp/claude-0/-home-user-Real-Time-Sound-Visualizer/fa175d99-1e8a-5677-be21-a0c5de1c3a3d/scratchpad/bin/"
OUT = "/home/user/Real-Time-Sound-Visualizer/web/docs/listening/one-to-two"
os.makedirs(OUT, exist_ok=True)
F0 = meas.hz(36)
Q = 1 / (4 * F0) / 16          # a sixteenth of a turn of the dyad's drift (the right runs 4 f faster at ratio 5)
REL_IN, REL_ANTI = rend.T_UPOFF + 2 * Q, rend.T_UPOFF + 10 * Q
def seq(rel): return [(rend.T_BASS, 0x90, 36, 100), (rend.T_UP, 0x90, 64, 100), (rel, 0x80, 64, 0), (rend.T_BASSOFF, 0x80, 36, 0)]
ALONE = [(rend.T_BASS, 0x90, 36, 100), (rend.T_BASSOFF, 0x80, 36, 0)]
HT = rend.HT
DY, PO = HT, dict(HT, midiMode="poly", polyRound=True)
SP = dict(PO, layers="split", splitAt=55)
TAKES = [
 ("dyad-today", "Today, in Dyad (as Harmonic tone ships)", DY, "render_cpp", REL_IN, "today"),
 ("dyad-today-later", "Today, in Dyad, the high note let go 1.9 ms later", DY, "render_cpp", REL_ANTI, "today"),
 ("poly-today", "Today, in Poly (Quarter turn on)", PO, "render_cpp", REL_IN, "today"),
 ("split-today", "Today, in a split at G3 (each hand its own)", SP, "render_cpp", REL_IN, "today"),
 ("dyad-instep", "A. Dyad: the right put back in step, over 30 ms", DY, "r-instep", REL_IN, "A"),
 ("dyad-lean", "B. Dyad: A, and the bass kept half in the right with its quarter turn", DY, "r-lean", REL_IN, "B"),
 ("poly-turn", "C. Poly: the quarter turn kept on the outer notes", PO, "r-turn", REL_IN, "C"),
 ("poly-nolean", "D. Poly: no lean, every note keeps its own image", PO, "r-nolean", REL_IN, "D"),
]
def wav(path, L, R):
    n = len(L); fade = int(0.05 * rend.RATE)
    g = np.minimum(1.0, (n - 1 - np.arange(n)) / fade)
    x = np.empty(2 * n); x[0::2] = L * g; x[1::2] = R * g
    data = np.round(np.clip(x, -1, 1) * 32767).astype("<i2").tobytes()
    hdr = b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt " + struct.pack("<IHHIIHH", 16, 1, 2, rend.RATE, rend.RATE * 4, 4, 16) \
        + b"data" + struct.pack("<I", len(data))
    open(path, "wb").write(hdr + data)
def figure(L, R, t, span=2 / F0):
    i = int(t * rend.RATE); n = int(span * rend.RATE)
    x, y = L[i:i + n], R[i:i + n]
    m = max(np.abs(x).max(), np.abs(y).max(), 1e-9)
    return [[round(float(a / m), 3), round(float(b / m), 3)] for a, b in zip(x[::2], y[::2])]
def image(fields, exe, rel):
    """The bass's own image with the picture off: alone, with the high note, and back."""
    L, R, out = rend.render(dict(fields, pictureAmount=0), "img", events=seq(rel), exe=B + exe, every=0)
    tr = meas.track(L, R, F0)
    T1, T2, T3 = rend.T_UP, rel, rend.T_BASSOFF
    im = {"alone": summ.bass_image(tr, T1 - 0.6, T1 - 0.05), "with": summ.bass_image(tr, T1 + 0.08, T2 - 0.05),
          "back": summ.bass_image(tr, T2 + 0.08, T3 - 0.05)}
    for k in im.values():
        k["lr"] = k["R"] - k["L"]
        k["power"] = 10 * np.log10(10 ** (k["L"] / 10) + 10 ** (k["R"] / 10))
    im["fig_alone"] = figure(L, R, T1 - 0.3); im["fig_with"] = figure(L, R, T1 + 0.5); im["fig_back"] = figure(L, R, T2 + 0.5)
    return im
def picture(fields, exe, rel):
    """With the picture on, as shipped: how far the bass's timbre and level wander from the same bass held alone."""
    L, R, out = rend.render(fields, "pic", events=seq(rel), exe=B + exe, every=0.01, reads=("limiter", "loop"))
    a = rend.render(fields, "pica", events=ALONE, exe=B + exe, every=0.01, reads=("limiter", "loop"))
    r = summ.summary(L, R, out, alone=a)
    return L, R, {"cent_vs_alone": r["cent_vs_alone"], "lvl_vs_alone": r["lvl_vs_alone"], "lim": r["lim"],
                  "back_phase": r["after_late"]["phase"], "back_coh": r["after_late"]["coh"]}
def sweep(exe):
    out = []
    for k in range(16):
        rel = rend.T_UPOFF + k * Q
        L, R, _ = rend.render(dict(DY, pictureAmount=0), "sw", events=seq(rel), exe=B + exe, every=0)
        im = summ.bass_image(meas.track(L, R, F0), rel + 0.2, rend.T_BASSOFF - 0.05)
        out.append([round(im["phase"]), round(im["coh"], 2)])
    return out
if __name__ == "__main__":
    numbers = {"takes": [], "sweep": {}, "rel": [REL_IN, REL_ANTI], "times": [rend.T_BASS, rend.T_UP, rend.T_UPOFF, rend.T_BASSOFF, rend.END]}
    for name, label, fields, exe, rel, group in TAKES:
        L, R, pic = picture(fields, exe, rel)
        wav(os.path.join(OUT, name + ".wav"), L, R)
        open(os.path.join(OUT, name + ".b64.txt"), "w").write(base64.b64encode(open(os.path.join(OUT, name + ".wav"), "rb").read()).decode())
        im = image(fields, exe, rel)
        numbers["takes"].append({"file": name, "label": label, "group": group, "fields": fields, "exe": exe, "release": rel,
                                 "image": im, "picture": pic, "peak": [float(np.abs(L).max()), float(np.abs(R).max())]})
        print(name, json.dumps({k: {kk: round(vv, 2) for kk, vv in v.items() if not isinstance(vv, list)} for k, v in im.items() if not k.startswith("fig")}), json.dumps(pic), flush=True)
    for exe in ("render_cpp", "r-instep"):
        numbers["sweep"][exe] = sweep(exe); print(exe, numbers["sweep"][exe], flush=True)
    json.dump(numbers, open("numbers.json", "w"), indent=1)
