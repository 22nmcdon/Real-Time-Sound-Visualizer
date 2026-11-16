import sys, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
import rend, meas
def slots(out):
    rows = rend.readings(out).get("loop", [])
    t = np.array([r[0] for r in rows]); S = {}
    for r in rows:
        for f in r[1]:
            if ":" in f:
                s, h, _ = f.split(":"); S.setdefault(int(s), []).append(float(h))
    return t, {k: np.array(v) for k, v in S.items()}
NAMES = {22: "fold", 24: "echo", 18: "twist", 2: "phase", 35: "phaser", 19: "fm", 21: "drive", 23: "vcf", 37: "reverb"}
def figure(runs, path, f0=meas.hz(36)):
    fig, ax = plt.subplots(6, 1, figsize=(12, 16), sharex=True)
    for name, (L, R, out) in runs.items():
        tr = meas.track(L, R, f0)
        ax[0].plot(tr["t"], tr["L"], label=name + " L"); ax[0].plot(tr["t"], tr["R"], "--", label=name + " R")
        ax[1].plot(tr["t3"], tr["bassL"], label=name + " bass L"); ax[1].plot(tr["t3"], tr["bassR"], "--", label=name + " bass R")
        ax[2].plot(tr["t2"], tr["corr"], label=name)
        ax[3].plot(tr["t3"], tr["dphi"], label=name)
        ax[4].plot(tr["t3"], tr["centL"], label=name + " L"); ax[4].plot(tr["t3"], tr["centR"], "--", label=name + " R")
        t, S = slots(out)
        for k, v in S.items():
            if np.abs(v).max() > 1e-6: ax[5].plot(t, v, label=name + " " + NAMES.get(k, str(k)))
    for a, y in zip(ax, ("ear dB", "bass's own dB", "corr", "bass R-L phase", "bass centroid (harmonic no.)", "loop depth")):
        a.set_ylabel(y); a.legend(fontsize=7); a.grid(alpha=.3)
        for e in (rend.T_BASS, rend.T_UP, rend.T_UPOFF, rend.T_BASSOFF): a.axvline(e, color="k", lw=.5)
    ax[1].set_ylim(-60, 0); ax[0].set_ylim(-50, 0)
    fig.tight_layout(); fig.savefig(path, dpi=60)
if __name__ == "__main__":
    pass
