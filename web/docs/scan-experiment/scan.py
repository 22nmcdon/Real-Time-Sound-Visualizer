"""Scan the recorded phosphor: brightness along a closed path, each frame, as a
single-cycle table played at a held note. Open loop - the scan's sound is not drawn
back - which is enough to answer the experiment's question: can a scanned phosphor
sound good at all."""
import json, os, sys, wave
import numpy as np

SR, N, FPS = 44100, 2048, 60
NOTES = [110.0, 164.81, 220.0]          # A2, E3, A3, a second each

def blur(g, sigma):
    if sigma <= 0: return g
    r = int(np.ceil(3 * sigma)); x = np.arange(-r, r + 1)
    k = np.exp(-x * x / (2 * sigma * sigma)); k /= k.sum()
    g = np.apply_along_axis(lambda v: np.convolve(v, k, mode="same"), 1, g)
    return np.apply_along_axis(lambda v: np.convolve(v, k, mode="same"), 0, g)

def bilinear(g, u, v):
    # The page's phosphorReadGrid: cell centres at (i + 0.5) / 64, nought outside.
    n = g.shape[0]; fx = u * n - 0.5; fy = v * n - 0.5
    x0 = np.floor(fx).astype(int); y0 = np.floor(fy).astype(int); tx = fx - x0; ty = fy - y0
    def cell(cx, cy):
        ok = (cx >= 0) & (cy >= 0) & (cx < n) & (cy < n)
        return np.where(ok, g[np.clip(cy, 0, n - 1), np.clip(cx, 0, n - 1)], 0.0)
    return (cell(x0, y0) * (1 - tx) * (1 - ty) + cell(x0 + 1, y0) * tx * (1 - ty)
            + cell(x0, y0 + 1) * (1 - tx) * ty + cell(x0 + 1, y0 + 1) * tx * ty)

def frame_geometry(frames):
    # One fixed path per preset, around where the figure is on average: a centroid
    # that moved every frame would move the path and smear the table.
    c = (np.arange(64) + 0.5) / 64; X, Y = np.meshgrid(c, c)
    w = frames.mean(axis=0); s = w.sum()
    cx, cy = (X * w).sum() / s, (Y * w).sum() / s
    r = np.sqrt((((X - cx) ** 2 + (Y - cy) ** 2) * w).sum() / s)
    return cx, cy, r

def path(kind, cx, cy, r):
    t = np.arange(N) / N * 2 * np.pi
    if kind == "wide":  return cx + r * np.cos(t), cy + r * np.sin(t)
    if kind == "tight": return cx + 0.5 * r * np.cos(t), cy + 0.5 * r * np.sin(t)
    if kind == "lissajous": return cx + r * np.cos(2 * t), cy + r * np.sin(3 * t)
    # Off the figure's centre: a symmetric figure read from its centre repeats
    # within one lap, so the table's lowest harmonic is the figure's symmetry and
    # the note sounds that many times too high. Read from off-centre, it cannot.
    if kind == "offset": return cx + 0.35 * r + 0.8 * r * np.cos(t), cy + 0.2 * r + 0.8 * r * np.sin(t)
    raise ValueError(kind)

def tables(frames, kind, softness):
    cx, cy, r = frame_geometry(frames)
    u, v = path(kind, cx, cy, r)
    out, last = [], np.zeros(N)
    for g in frames:
        t = bilinear(blur(g, softness), u, v)
        t = t - t.mean()
        rms = np.sqrt((t * t).mean())
        # A path through darkness reads nothing; hold the last table rather than divide by it.
        if rms > 1e-4: last = t / rms
        out.append(last.copy())
    return np.array(out)

def metrics(tabs):
    H = np.abs(np.fft.rfft(tabs, axis=1))[:, 1:65]           # harmonics 1..64
    P = H ** 2; tot = P.sum(axis=1) + 1e-12
    h = np.arange(1, 65)
    db = 20 * np.log10(H[:, :32] + 1e-9)
    slope = np.array([np.polyfit(np.log2(h[:32]), d, 1)[0] for d in db])
    crest = np.abs(tabs).max(axis=1) / (np.sqrt((tabs ** 2).mean(axis=1)) + 1e-12)
    motion = (np.abs(np.diff(H[:, :32], axis=0)).sum(axis=1) / (H[1:, :32].sum(axis=1) + 1e-12))
    # The harmonic the ear takes for the pitch: the lowest carrying a tenth of the energy.
    lowest = np.array([int(np.argmax(row / t > 0.1)) + 1 for row, t in zip(P, tot)])
    return {"lowest": float(np.median(lowest)), "crest": float(np.median(crest)), "slope_db_oct": float(np.median(slope)),
            "centroid_h": float(np.median((P * h).sum(axis=1) / tot)),
            "fundamental": float(np.median(P[:, 0] / tot)), "motion": float(np.mean(motion))}

def render(tabs):
    spf = SR // FPS; total = spf * len(tabs)
    out = np.zeros(total); phase = 0.0
    per_note = len(tabs) // len(NOTES)
    for n, f0 in enumerate(NOTES):
        kmax = int((SR / 2) / f0 * 0.9)                        # band-limited, as the drawn cycle is
        for i in range(n * per_note, (n + 1) * per_note):
            spec = []
            for j in (i, min(i + 1, len(tabs) - 1)):
                S = np.fft.rfft(tabs[j]); S[kmax + 1:] = 0; spec.append(np.fft.irfft(S, N))
            a, b = spec
            idx = np.arange(spf); xf = idx / spf                # crossfade across the frame
            ph = (phase + f0 * N / SR * (idx + 1)) % N
            p0 = np.floor(ph).astype(int); fr = ph - p0; p1 = (p0 + 1) % N
            sa = a[p0] * (1 - fr) + a[p1] * fr; sb = b[p0] * (1 - fr) + b[p1] * fr
            out[i * spf:(i + 1) * spf] = sa * (1 - xf) + sb * xf
            phase = ph[-1]
        # Each note its own envelope: 10 ms in, 60 ms out, so the joins do not click.
        s0, s1 = n * per_note * spf, (n + 1) * per_note * spf
        env = np.ones(s1 - s0); a_ = int(0.01 * SR); r_ = int(0.06 * SR)
        env[:a_] = np.linspace(0, 1, a_); env[-r_:] = np.linspace(1, 0, r_)
        out[s0:s1] *= env
    rms = np.sqrt((out ** 2).mean()) + 1e-12
    out = out * (0.1 / rms)                                   # every file at -20 dBFS RMS
    return np.clip(out, -0.99, 0.99)

def write_wav(path_, x):
    with wave.open(path_, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype("<i2").tobytes())

def reference(shape):
    t = np.arange(N) / N
    tab = (2 * t - 1) if shape == "saw" else np.sin(2 * np.pi * t)
    tab = (tab - tab.mean()) / np.sqrt(((tab - tab.mean()) ** 2).mean())
    return np.repeat(tab[None, :], 180, axis=0)

def main(GRIDS, OUT):
    results = {}
    os.makedirs(OUT, exist_ok=True)
    for ref in ("sine", "saw"):
        tabs = reference(ref); results["ref-" + ref] = {"preset": "reference", "path": ref, "softness": 0, **metrics(tabs)}
        write_wav(os.path.join(OUT, "ref-%s.wav" % ref), render(tabs))
    for fn in sorted(os.listdir(GRIDS)):
        if not fn.endswith(".npy"): continue
        frames = np.load(os.path.join(GRIDS, fn)).astype(np.float64)
        slug = fn[:-4]
        for kind in ("wide", "tight", "lissajous", "offset"):
            for soft in (0.0, 1.5, 3.0):
                tabs = tables(frames, kind, soft)
                key = "%s--%s--s%s" % (slug, kind, str(soft).replace(".", "_"))
                results[key] = {"preset": slug, "path": kind, "softness": soft, **metrics(tabs)}
                write_wav(os.path.join(OUT, key + ".wav"), render(tabs))
                np.save(os.path.join(OUT, key + "-tables.npy"), tabs[::30].astype(np.float32))
    json.dump(results, open(os.path.join(OUT, "metrics.json"), "w"), indent=1)
    print("%-44s %6s %6s %8s %7s %6s %7s" % ("variant", "lowest", "crest", "dB/oct", "centr", "fund", "motion"))
    for k, m in results.items():
        print("%-44s %6.0f %6.2f %8.2f %7.1f %6.3f %7.3f" % (k, m["lowest"], m["crest"], m["slope_db_oct"], m["centroid_h"], m["fundamental"], m["motion"]))

# Round two (scan2.py) imports the reading and the measures without running this.
if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
