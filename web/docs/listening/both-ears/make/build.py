"""Every take, figure and number on the both-ears listening page, into numbers.json and the page's directory."""
import base64, json, os, struct, sys
import numpy as np
import rend, bank
OUT = "/home/user/Real-Time-Sound-Visualizer/web/docs/listening/both-ears"
os.makedirs(OUT, exist_ok=True)
RATE = rend.RATE
def hz(n): return 440 * 2 ** ((n - 69) / 12)
F0 = hz(36)
TINE = bank.BANK["Tine piano"]
# The chord's notes made plain for measuring: Tine piano's voices without FM, Scan or its routings, held at full,
# so each note is one sine and its level in each ear can be read off its own fundamental. Its image is the
# voice's routing, which none of that touches.
TINE_PLAIN = dict(TINE, oscFm=0, oscScan=0, scanStrike=0, mod="", sus=100)
BUILDS = [("today", "render_cpp"), ("w1a", "r-w1a"), ("w1b", "r-w1b"), ("w1c", "r-w1c"), ("w2", "r-w2")]
LABEL = {"today": "Today", "w1a": "Way 1 (a): nearly mono", "w1b": "Way 1 (b): gentle width", "w1c": "Way 1 (c): wide",
         "w2": "Way 2: every note on both sides"}
# Q, a sixteenth of a turn of the dyad's drift (the one-to-two page's release moments).
Q = 1 / (4 * F0) / 16
REL = rend.T_UPOFF + 2 * Q
def owner(rel=REL):
    return [(rend.T_BASS, 0x90, 36, 100), (rend.T_UP, 0x90, 64, 100), (rel, 0x80, 64, 0), (rend.T_BASSOFF, 0x80, 36, 0)]

def lockin(L, R, f, a, b, win=0.12, hop=0.01):
    """A note's fundamental in each ear over [a, b): level (dB) each side, and the coherence of the two
    (cos of the phase between them, weighted by level: 1 the same in both ears, 0 a quarter turn)."""
    n = int(win * RATE); w = np.hanning(n); w /= w.sum()
    HL, HR = [], []
    for t in np.arange(a, b - win, hop):
        i = int(t * RATE)
        e = np.exp(-2j * np.pi * f * (i + np.arange(n)) / RATE) * w
        HL.append(2 * (L[i:i + n] @ e)); HR.append(2 * (R[i:i + n] @ e))
    HL, HR = np.array(HL), np.array(HR)
    db = lambda v: float(20 * np.log10(max(v, 1e-9)))
    lL = np.sqrt(np.mean(abs(HL) ** 2)); lR = np.sqrt(np.mean(abs(HR) ** 2))
    coh = float(np.real(np.sum(HL * np.conj(HR))) / max(np.sqrt(np.sum(abs(HL) ** 2) * np.sum(abs(HR) ** 2)), 1e-18))
    # the phase between them, swung per window: how much the image moves while nothing is played
    per = np.real(HL * np.conj(HR)) / np.maximum(abs(HL) * abs(HR), 1e-18)
    bal = 20 * np.log10(np.maximum(abs(HR), 1e-9) / np.maximum(abs(HL), 1e-9))
    return {"L": db(lL), "R": db(lR), "coh": coh, "coh_lo": float(np.percentile(per, 5)), "coh_hi": float(np.percentile(per, 95)),
            "bal_lo": float(np.percentile(bal, 5)), "bal_hi": float(np.percentile(bal, 95))}

def figure(X, Y, t, span, keep=320):
    i = int(t * RATE); n = int(span * RATE)
    x, y = X[i:i + n], Y[i:i + n]
    m = max(np.abs(x).max(), np.abs(y).max(), 1e-9)
    s = max(1, n // keep)
    return [[round(float(a / m), 3), round(float(b / m), 3)] for a, b in zip(x[::s], y[::s])]

def wav(path, L, R):
    n = len(L); fade = int(0.05 * RATE)
    g = np.minimum(1.0, (n - 1 - np.arange(n)) / fade)
    x = np.empty(2 * n); x[0::2] = L * g; x[1::2] = R * g
    data = np.round(np.clip(x, -1, 1) * 32767).astype("<i2").tobytes()
    hdr = b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt " + struct.pack("<IHHIIHH", 16, 1, 2, RATE, RATE * 4, 4, 16) \
        + b"data" + struct.pack("<I", len(data))
    open(path, "wb").write(hdr + data)
    open(path[:-4] + ".b64.txt", "w").write(base64.b64encode(open(path, "rb").read()).decode())

# The owner's phrase's three spans, and the chord's seven.
OWNER_SPANS = [("alone", rend.T_UP - 0.6, rend.T_UP - 0.05), ("with the E", rend.T_UP + 0.08, rend.T_UPOFF - 0.05),
               ("alone again", rend.T_UPOFF + 0.08, rend.T_BASSOFF - 0.05)]
ev = sorted([t for t in rend.CHORD_ON] + list(rend.CHORD_OFF.values()))
CHORD_SPANS = []
names = ["C3", "C3 E3", "C3 E3 G3", "C3 E3 G3 C4", "C3 E3 G3", "C3 E3", "C3"]
for k in range(7):
    CHORD_SPANS.append((names[k], ev[k] + 0.08, ev[k + 1] - 0.05))
CHORD_HZ = {"C3": hz(48), "E3": hz(52), "G3": hz(55), "C4": hz(60)}

def measure_owner(exe):
    r = rend.render(exe, dict(rend.HT, pictureAmount=0), owner(), rend.END, "m-owner-" + exe, limiter=False)
    out = {}
    for name, a, b in OWNER_SPANS:
        out[name] = {"C2": lockin(r["L"], r["R"], F0, a, b)}
        if name == "with the E": out[name]["E4"] = lockin(r["L"], r["R"], 5 * F0, a, b)
    figs = {"drawn": [figure(r["X"], r["Y"], (a + b) / 2, 2 / F0) for _, a, b in OWNER_SPANS],
            "heard": [figure(r["L"], r["R"], (a + b) / 2, 2 / F0) for _, a, b in OWNER_SPANS]}
    return out, figs

def sweep_owner(exe):
    """The bass's coherence once alone again, for sixteen release moments across one turn of the drift."""
    v = []
    for k in range(16):
        rel = rend.T_UPOFF + k * Q
        r = rend.render(exe, dict(rend.HT, pictureAmount=0), owner(rel), rend.END, "sw", full=False, every=0, limiter=False)
        v.append(round(lockin(r["L"], r["R"], F0, rel + 0.2, rend.T_BASSOFF - 0.05)["coh"], 2))
    return v

def measure_chord(exe):
    r = rend.render(exe, TINE_PLAIN, rend.CHORD, rend.CHORD_END, "m-chord-" + exe, limiter=False)
    out = [[name, {n: lockin(r["L"], r["R"], CHORD_HZ[n], a, b) for n in name.split()}] for name, a, b in CHORD_SPANS]
    # The limiter's share, apart: the held C3's level in both ears with it on, against with it off.
    on = rend.render(exe, TINE_PLAIN, rend.CHORD, rend.CHORD_END, "m-chordlim-" + exe, full=False)
    for k, (name, a, b) in enumerate(CHORD_SPANS):
        out[k][1]["C3"]["lim"] = lockin(on["L"], on["R"], CHORD_HZ["C3"], a, b)["L"] - out[k][1]["C3"]["L"]
    return out

def picture_on_owner(exe):
    """With the picture on, as shipped: how far the held bass's image swings while nothing is played."""
    r = rend.render(exe, rend.HT, owner(), rend.END, "p-owner-" + exe, full=False)
    return {name: lockin(r["L"], r["R"], F0, a, b) for name, a, b in OWNER_SPANS}

if __name__ == "__main__":
    N = {"builds": BUILDS, "label": LABEL, "owner": {}, "chord": {}, "sweep": {}, "picture": {}, "figs": {}, "takes": [],
         "owner_spans": OWNER_SPANS, "chord_spans": CHORD_SPANS, "release": REL}
    for key, exe in BUILDS:
        N["owner"][key], N["figs"]["owner-" + key] = measure_owner(exe)
        N["chord"][key] = measure_chord(exe)
        N["sweep"][key] = sweep_owner(exe)
        N["picture"][key] = picture_on_owner(exe)
        print(key, json.dumps({s: {n: [round(v["L"], 1), round(v["R"], 1), round(v["coh"], 2)] for n, v in d.items()} for s, d in N["owner"][key].items()}))
        print("   chord", json.dumps([[s, {n: [round(v["L"], 1), round(v["R"], 1), round(v["coh"], 2)] for n, v in d.items()}, round(d["C3"]["lim"], 2)] for s, d in N["chord"][key]]))
        print("   sweep", N["sweep"][key])
        print("   picture-on bass", json.dumps({s: [round(d["bal_lo"], 1), round(d["bal_hi"], 1), round(d["coh_lo"], 2), round(d["coh_hi"], 2)] for s, d in N["picture"][key].items()}), flush=True)
    # The takes, as shipped (the picture on), and the figures the screen draws in each.
    TAKES = [("owner-today", "owner", "today"), ("owner-w1a", "owner", "w1a"), ("owner-w1b", "owner", "w1b"),
             ("owner-w1c", "owner", "w1c"), ("owner-w2", "owner", "w2"),
             ("chord-today", "chord", "today"), ("chord-w1b", "chord", "w1b"), ("chord-w2", "chord", "w2")]
    exe_of = dict(BUILDS)
    for name, phrase, key in TAKES:
        if phrase == "owner":
            r = rend.render(exe_of[key], rend.HT, owner(), rend.END, "t-" + name)
            spans, span = OWNER_SPANS, 2 / F0
        else:
            r = rend.render(exe_of[key], TINE, rend.CHORD, rend.CHORD_END, "t-" + name)
            spans, span = CHORD_SPANS, 2 / hz(48)
        wav(os.path.join(OUT, name + ".wav"), r["L"], r["R"])
        t = {"file": name, "phrase": phrase, "key": key,
             "drawn": [figure(r["X"], r["Y"], (a + b) / 2, span) for _, a, b in spans],
             "heard": [figure(r["L"], r["R"], (a + b) / 2, span) for _, a, b in spans],
             "peak": [float(np.abs(r["L"]).max()), float(np.abs(r["R"]).max())],
             "rms_db": float(10 * np.log10(np.mean(r["L"] ** 2 + r["R"] ** 2) / 2))}
        N["takes"].append(t)
        print(name, t["peak"], round(t["rms_db"], 1), flush=True)
    json.dump(N, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "numbers.json"), "w"))
