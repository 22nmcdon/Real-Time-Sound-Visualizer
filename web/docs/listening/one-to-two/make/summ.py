import numpy as np, rend, meas
def bass_image(tr, a, b):
    """The bass's own image over [a, b): each ear's level of its harmonics (dB), its
    fundamental's phase right against left, and its interaural coherence (cos of it,
    weighted by level), and its centroid."""
    t = tr["t3"]; s = (t >= a) & (t < b)
    H1L, H1R = tr["H"][1][0][s], tr["H"][1][1][s]
    coh = float(np.real(np.sum(H1L * np.conj(H1R))) / max(np.sqrt(np.sum(abs(H1L) ** 2) * np.sum(abs(H1R) ** 2)), 1e-18))
    ph = float(np.degrees(np.angle(np.sum(H1R * np.conj(H1L)))))
    return dict(L=float(np.mean(tr["bassL"][s])), R=float(np.mean(tr["bassR"][s])), coh=coh, phase=ph,
                cent=float(np.mean(tr["centL"][s])))
def swing(tr, a, b):
    """How far the balance between the ears moves over [a, b): the range (5th to 95th) of L minus R in dB."""
    t = tr["t"]; s = (t >= a) & (t < b)
    d = tr["L"][s] - tr["R"][s]
    return float(np.percentile(d, 95) - np.percentile(d, 5)), float(np.median(d))
def onset(L, R, ev, f0, before=0.15, after=0.4):
    """How fast the bass's right-ear share changes at an event: a fine lock-in (20 ms) on its
    fundamental in each ear, the time from the event to 90 per cent of the change."""
    tr = meas.track(L, R, f0, hop_s=0.001, lock_s=0.03)
    t = tr["t3"]
    r = np.abs(tr["H"][1][1]); l = np.abs(tr["H"][1][0])
    v = 20 * np.log10(np.maximum(r, 1e-6) / np.maximum(l, 1e-6))   # right against left
    b = np.mean(v[(t > ev - before) & (t < ev - 0.03)]); a_ = np.mean(v[(t > ev + after - 0.1) & (t < ev + after)])
    d = a_ - b
    s = (t > ev - 0.03) & (t < ev + after); frac = (v[s] - b) / d if abs(d) > 0.5 else None
    took = float(t[s][np.where(frac >= 0.9)[0][0]] - ev) if frac is not None and (frac >= 0.9).any() else float("nan")
    return float(b), float(a_), float(took)
def limiter(out, a, b):
    rows = rend.readings(out).get("limiter", [])
    v = [float(r[1][0]) for r in rows if a <= r[0] < b]
    return min(v) if v else float("nan")
def summary(L, R, out, f0=meas.hz(36), alone=None):
    tr = meas.track(L, R, f0)
    T0, T1, T2, T3 = rend.T_BASS, rend.T_UP, rend.T_UPOFF, rend.T_BASSOFF
    res = {"before": bass_image(tr, T1 - 0.6, T1 - 0.05), "with": bass_image(tr, T1 + 0.08, T1 + 0.4),
           "with_late": bass_image(tr, T2 - 0.6, T2 - 0.05),
           "after": bass_image(tr, T2 + 0.08, T2 + 0.4), "after_late": bass_image(tr, T3 - 0.8, T3 - 0.05),
           "swing_before": swing(tr, T0 + 0.4, T1 - 0.05), "swing_after": swing(tr, T2 + 0.3, T3 - 0.05),
           "on": onset(L, R, T1, f0), "off": onset(L, R, T2, f0),
           "lim": [limiter(out, T0, T1), limiter(out, T1, T2), limiter(out, T2, T3)]}
    if alone is not None:
        ta = meas.track(*alone[:2], f0)
        s = (tr["t3"] > T1) & (tr["t3"] < T3)
        res["cent_vs_alone"] = float(np.mean(np.abs(tr["centL"][s] - ta["centL"][s])))
        res["lvl_vs_alone"] = float(np.mean(np.abs(tr["bassL"][s] - ta["bassL"][s])))
    return res
def line(name, r):
    f = lambda d: "L%6.1f R%6.1f coh%5.2f ph%5.0f c%4.1f" % (d["L"], d["R"], d["coh"], d["phase"], d["cent"])
    s = "%-28s before[%s]\n%28s with  [%s]\n%28s after [%s] late[%s]\n" % (name, f(r["before"]), "", f(r["with"]), "", f(r["after"]), f(r["after_late"]))
    s += "%28s R-L at entry %.1f->%.1f dB in %.3fs, exit %.1f->%.1f in %.3fs; swing before %.1f after %.1f dB; lim %s" % (
        "", *r["on"], *r["off"], r["swing_before"][0], r["swing_after"][0], ["%.1f" % x for x in r["lim"]])
    if "cent_vs_alone" in r: s += "; vs alone: centroid %.2f, level %.1f dB" % (r["cent_vs_alone"], r["lvl_vs_alone"])
    return s
