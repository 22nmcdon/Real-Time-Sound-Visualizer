"""What the bass note does, per ear and over time, through the owner's sequence."""
import numpy as np
import rend
RATE = rend.RATE
def hz(n): return 440 * 2 ** ((n - 69) / 12)
def frames(x, win, hop):
    n = (len(x) - win) // hop + 1
    idx = np.arange(win)[None, :] + hop * np.arange(n)[:, None]
    return x[idx]
def track(L, R, f0, hop_s=0.005, win_s=0.02, lock_s=0.1, ks=(1, 2, 3, 4, 6, 7, 8, 9)):
    """Per hop: each ear's RMS (dB), side over mid, correlation, and the bass's own
    harmonics in each ear by lock-in over a Hann window of lock_s (complex)."""
    hop = int(hop_s * RATE); win = int(win_s * RATE); lw = int(lock_s * RATE)
    out = {}
    fL, fR = frames(L, win, hop), frames(R, win, hop)
    t = (np.arange(len(fL)) * hop + win / 2) / RATE
    rl, rr = np.sqrt((fL ** 2).mean(1)), np.sqrt((fR ** 2).mean(1))
    db = lambda v: 20 * np.log10(np.maximum(v, 1e-9))
    out["t"] = t; out["L"] = db(rl); out["R"] = db(rr)
    # Width over 50 ms: side over mid, and correlation.
    w2 = int(0.05 * RATE)
    gL, gR = frames(L, w2, hop), frames(R, w2, hop)
    t2 = (np.arange(len(gL)) * hop + w2 / 2) / RATE
    m, s = (gL + gR) / 2, (gL - gR) / 2
    out["t2"] = t2
    out["sm"] = np.sqrt((s ** 2).mean(1)) / np.maximum(np.sqrt((m ** 2).mean(1)), 1e-12)
    num = (gL * gR).mean(1); den = np.sqrt((gL ** 2).mean(1) * (gR ** 2).mean(1))
    out["corr"] = num / np.maximum(den, 1e-12)
    # The bass's own harmonics by lock-in.
    hL, hR = frames(L, lw, hop), frames(R, lw, hop)
    t3 = (np.arange(len(hL)) * hop + lw / 2) / RATE
    w = np.hanning(lw); w /= w.sum()
    n = np.arange(lw)
    out["t3"] = t3
    H = {}
    for k in ks:
        # Each frame's own start time in the phase, so phases are absolute.
        e = np.exp(-2j * np.pi * k * f0 * n / RATE) * w
        st = np.exp(-2j * np.pi * k * f0 * (np.arange(len(hL)) * hop) / RATE)
        H[k] = (2 * (hL @ e) * st, 2 * (hR @ e) * st)
    out["H"] = H
    clean = [k for k in ks]
    out["bassL"] = db(np.sqrt(sum(np.abs(H[k][0]) ** 2 for k in clean) / 2))
    out["bassR"] = db(np.sqrt(sum(np.abs(H[k][1]) ** 2 for k in clean) / 2))
    def cent(i):
        a = np.array([np.abs(H[k][i]) ** 2 for k in clean]); kk = np.array(clean)[:, None]
        return (a * kk).sum(0) / np.maximum(a.sum(0), 1e-18)
    out["centL"], out["centR"] = cent(0), cent(1)
    # The bass fundamental's phase in the right against the left, in degrees (what its quarter turn is).
    out["dphi"] = np.degrees(np.angle(H[1][1] / np.where(np.abs(H[1][0]) > 0, H[1][0], 1)))
    out["h3L"] = db(np.abs(H[3][0])) - db(np.abs(H[1][0]))
    return out
def at(t, v, a, b):
    s = (t >= a) & (t < b)
    return float(np.mean(v[s])) if s.any() else float("nan")
def step(tr, key, tkey, ev, before=(0.5, 0.05), after=(0.35, 0.95)):
    """Before and after an event: means, the change, and how long the change takes
    to get 90 per cent of the way (from the event)."""
    t, v = tr[tkey], tr[key]
    b = at(t, v, ev - before[0], ev - before[1]); a = at(t, v, ev + after[0], ev + after[1])
    d = a - b
    s = (t >= ev - 0.05) & (t <= ev + after[1])
    tt, vv = t[s], v[s]
    took = float("nan")
    if abs(d) > 1e-9:
        frac = (vv - b) / d
        # first time it reaches 90% and the last time it is outside 10% of the final value
        reach = np.where(frac >= 0.9)[0]
        took = float(tt[reach[0]] - ev) if len(reach) else float("nan")
    return b, a, d, took
