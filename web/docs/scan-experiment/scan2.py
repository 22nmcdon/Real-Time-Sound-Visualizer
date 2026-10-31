"""The Scan experiment, round two: what makes a scanned phosphor jarring.

Round one's off-centre, softer takes had the right character and still sounded
jarring, and the owner heard it in every picture. Two causes were in the render,
not the pictures:

- Motion grain. Each frame's table was crossfaded whole into the next, sixty
  times a second, and evened in level on its own. A picture that changes a
  little moves every harmonic's phase a little, so the crossfade dips and the
  level twitches at the frame rate: a 60 Hz grain over the note.
- Spikiness. A path crossing thin lit lines reads narrow pulses, so the table's
  harmonics stand in a jagged comb rather than a smooth slope: bright and nasal
  even when softened.

So four takes of each picture, each changing one thing, to hear which matters:

  A  round one's off-centre, softer take, rendered as it was (the comparison);
  B  eased: each harmonic's level from the scan, slewed over 150 ms, at a fixed
     phase, played by a bank of oscillators - the motion without the grain;
  C  eased and gentle: B with the comb smoothed across neighbouring harmonics
     and the top tilted down 3 dB an octave more - the tone without the spikes;
  D  with the tone: C beside the default sound (a sine with a little of its
     third harmonic) at equal level, as Scan would sit in the instrument.

Each plays A2 alone for a second, then an A minor chord (A2, C3, E3) for two,
every voice reading the same picture. Every file at the same loudness.

    python3 scan2.py grids/ out2/
"""
import json, os, sys
import numpy as np
from scan import SR, N, FPS, tables, write_wav

HERE = os.path.dirname(os.path.abspath(__file__))
SOFT = 3.0          # round one's softer take
EASE = 0.15         # seconds: how long a harmonic's level takes to follow the picture
K = 48              # harmonics read; the band limit cuts higher voices further
# A2 alone, then the chord: (start, stop, hertz) per voice, in seconds.
VOICES = [(0.0, 1.0, 110.0), (1.0, 3.0, 110.0), (1.0, 3.0, 130.81), (1.0, 3.0, 164.81)]
ATTACK, RELEASE = 0.015, 0.12

def envelope(n):
    e = np.ones(n); a, r = int(ATTACK * SR), int(RELEASE * SR)
    e[:a] = np.linspace(0, 1, a); e[-r:] = np.linspace(1, 0, r)
    return e

def round_one(tabs, total):
    # Round one's render, voice by voice: whole tables crossfaded across each frame.
    out = np.zeros(total); spf = SR // FPS
    for t0, t1, f0 in VOICES:
        s0, s1 = int(t0 * SR), int(t1 * SR)
        kmax = int((SR / 2) / f0 * 0.9)
        band = []
        for tab in tabs:
            S = np.fft.rfft(tab); S[kmax + 1:] = 0; band.append(np.fft.irfft(S, N))
        n = np.arange(s0, s1)
        frame = np.minimum(n // spf, len(tabs) - 1); nxt = np.minimum(frame + 1, len(tabs) - 1)
        xf = (n % spf) / spf
        ph = (f0 * N / SR * (n - s0 + 1)) % N
        p0 = np.floor(ph).astype(int); fr = ph - p0; p1 = (p0 + 1) % N
        A = np.array(band)
        sa = A[frame, p0] * (1 - fr) + A[frame, p1] * fr
        sb = A[nxt, p0] * (1 - fr) + A[nxt, p1] * fr
        out[s0:s1] += (sa * (1 - xf) + sb * xf) * envelope(s1 - s0)
    return out

def harmonics(tabs, gentle):
    # Each frame's harmonic levels, eased over EASE, and evened in level after
    # easing rather than frame by frame.
    H = np.abs(np.fft.rfft(tabs, axis=1))[:, 1:K + 1]
    if gentle:
        # The comb smoothed across neighbouring harmonics, in level (dB), then
        # three decibels an octave more fall.
        L = 20 * np.log10(H + 1e-9)
        k = np.array([0.25, 0.5, 0.25])
        L = np.array([np.convolve(np.pad(row, 1, mode="edge"), k, mode="valid") for row in L])
        H = 10 ** (L / 20) / np.sqrt(np.arange(1, K + 1))
    a = 1 - np.exp(-1 / (EASE * FPS))
    out = np.empty_like(H); level = H[0].copy()
    for i, row in enumerate(H):
        level += a * (row - level); out[i] = level
    return out / (np.sqrt((out ** 2).sum(axis=1, keepdims=True)) + 1e-12)

# Fixed phases spread as Schroeder's, so the bank does not pile up into a click
# once a cycle, which all harmonics at nought phase would.
PHASES = -np.pi * np.arange(1, K + 1) * np.arange(0, K) / K

def bank(levels, total):
    out = np.zeros(total); spf = SR // FPS
    for t0, t1, f0 in VOICES:
        s0, s1 = int(t0 * SR), int(t1 * SR)
        n = np.arange(s0, s1)
        pos = np.minimum(n / spf, len(levels) - 1.0001)
        i0 = pos.astype(int); fr = (pos - i0)[:, None]
        amp = levels[i0] * (1 - fr) + levels[i0 + 1] * fr            # each harmonic's level, sample by sample
        kmax = min(K, int((SR / 2) / f0 * 0.9))
        t = (n - s0) / SR
        voice = np.zeros(s1 - s0)
        for k in range(1, kmax + 1):
            voice += amp[:, k - 1] * np.sin(2 * np.pi * k * f0 * t + PHASES[k - 1])
        out[s0:s1] += voice * envelope(s1 - s0)
    return out

def tone(total):
    # The default sound: a sine with a little of its third harmonic.
    out = np.zeros(total)
    for t0, t1, f0 in VOICES:
        s0, s1 = int(t0 * SR), int(t1 * SR); t = np.arange(s1 - s0) / SR
        out[s0:s1] += (np.sin(2 * np.pi * f0 * t) + 0.2 * np.sin(2 * np.pi * 3 * f0 * t)) * envelope(s1 - s0)
    return out

def level(x, rms=0.1):
    return np.clip(x * (rms / (np.sqrt((x ** 2).mean()) + 1e-12)), -0.99, 0.99)

def grain(x):
    """How much the sound's spectrum steps from one picture frame to the next
    while A2 is held alone: the mean change in a 4096-point spectrum between
    hops of one frame, over its size. The 60 Hz stepping of a whole-table
    crossfade shows here; a slewed bank does not step."""
    spf = SR // FPS; w = np.hanning(4096); S = []
    for s in range(int(0.15 * SR), int(0.85 * SR) - 4096, spf):
        S.append(np.abs(np.fft.rfft(x[s:s + 4096] * w))[:600])
    S = np.array(S)
    return float(np.mean(np.abs(np.diff(S, axis=0)).sum(axis=1) / (S[1:].sum(axis=1) + 1e-12)))

def slope(levels):
    # How fast the harmonics fall, in dB an octave, by the median frame.
    h = np.arange(1, 33)
    return float(np.median([np.polyfit(np.log2(h), 20 * np.log10(row[:32] + 1e-9), 1)[0] for row in levels]))

def main(grids, out):
    os.makedirs(out, exist_ok=True)
    total = int(3.0 * SR)
    results = {}
    for fn in sorted(os.listdir(grids)):
        if not fn.endswith(".npy"): continue
        slug = fn[:-4]
        frames = np.load(os.path.join(grids, fn)).astype(np.float64)
        tabs = tables(frames, "offset", SOFT)
        eased, gentle = harmonics(tabs, False), harmonics(tabs, True)
        takes = {"a-round-one": round_one(tabs, total), "b-eased": bank(eased, total),
                 "c-gentle": bank(gentle, total)}
        c = level(takes["c-gentle"]); takes["d-with-tone"] = level(c) + level(tone(total))
        raw = np.abs(np.fft.rfft(tabs, axis=1))[:, 1:K + 1]
        for take, x in takes.items():
            x = level(x)
            write_wav(os.path.join(out, "%s--%s.wav" % (slug, take)), x)
            results["%s--%s" % (slug, take)] = {"grain": grain(x)}
        results[slug + "--a-round-one"]["slope"] = slope(raw)
        results[slug + "--b-eased"]["slope"] = slope(eased)
        results[slug + "--c-gentle"]["slope"] = slope(gentle)
    ref = level(tone(total)); write_wav(os.path.join(out, "ref-tone.wav"), ref)
    results["ref-tone"] = {"grain": grain(ref)}
    json.dump(results, open(os.path.join(out, "metrics2.json"), "w"), indent=1)
    for k, m in results.items():
        print("%-36s grain %.4f%s" % (k, m["grain"], ("   %.1f dB/oct" % m["slope"]) if "slope" in m else ""))

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
