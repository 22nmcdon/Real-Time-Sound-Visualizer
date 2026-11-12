"""What the painting reads from a rendered phrase: the core's own voices
(render.cpp's log) for which note sounds, how loud and whether the key is
down, and the heard pair for everything a listener hears of the whole -
loudness, brightness, how fast the spectrum is changing, how noisy it is.

Everything a mark is made from comes out of here; `paint.py` invents nothing
the sound does not contain beyond where a mark lands, which the layouts
choose for composition (painting-the-sound.md allows that). The frame is
10 ms (480 samples at 48 kHz), the FFT 2048 samples (43 ms) under a Hann.
"""
import json, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(os.path.dirname(HERE), "build")
HOP, N = 480, 2048


def voices_log(name):
    """Per block: time, each layer's picture coverage, and the voices as
    (layer, note, hz, level, held)."""
    rows = []
    for line in open(os.path.join(BUILD, name + ".voices.txt")):
        head, _, rest = line.partition("|")
        t, ca, cb = map(float, head.split())
        vs = []
        for chunk in rest.split(";"):
            p = chunk.split()
            if len(p) == 5: vs.append((int(p[0]), int(p[1]), float(p[2]), float(p[3]), int(p[4])))
        rows.append((t, ca, cb, vs))
    return rows


def audio_frames(x, rate):
    mono = x.mean(axis=1)
    n = 1 + (len(mono) - N) // HOP
    win = np.hanning(N)
    idx = np.arange(N)[None, :] + HOP * np.arange(n)[:, None]
    spec = np.abs(np.fft.rfft(mono[idx] * win, axis=1)) + 1e-9
    freqs = np.fft.rfftfreq(N, 1 / rate)
    band = (freqs > 30) & (freqs < 12000)
    s, f = spec[:, band], freqs[band]
    power = s ** 2
    tot = power.sum(axis=1)
    centroid = (power * f).sum(axis=1) / tot
    spread = np.sqrt((power * (f - centroid[:, None]) ** 2).sum(axis=1) / tot)
    flatness = np.exp(np.log(s).mean(axis=1)) / s.mean(axis=1)
    rms = np.sqrt((mono[idx] ** 2).mean(axis=1))
    db = 20 * np.log10(rms + 1e-6)
    # Flux on the log spectrum, half-wave rectified: how much new energy
    # arrived since the last frame - the onsets, and between them how restless.
    ls = np.log(s)
    flux = np.concatenate([[0], np.maximum(ls[1:] - ls[:-1], 0).mean(axis=1)])
    # Change of shape regardless of level: the power spectrum as a
    # distribution, and half the distance from one frame to the next - nought
    # for a held, steady sound, one for a spectrum replaced outright. Power,
    # not magnitude, so the strong partials decide it and the floor between
    # them, which flickers in any sound, does not.
    shape = power / tot[:, None]
    unrest = np.concatenate([[0], 0.5 * np.abs(shape[1:] - shape[:-1]).sum(axis=1)])
    t = (np.arange(n) * HOP + N / 2) / rate
    return dict(t=t, db=db, centroid=centroid, spread=spread, flatness=flatness, flux=flux, unrest=unrest)


FIFTHS = {pc: (pc * 7) % 12 for pc in range(12)}


def fifths_distance(a, b):
    d = (FIFTHS[(a - b) % 12]) % 12
    return min(d, 12 - d)


def role_of(note, sounding):
    """A note's ink role against the lowest note sounding with it, by its
    distance round the circle of fifths: unison, fifth and fourth are the
    hand's own ink, the steps between two and four (seconds, thirds, sixths,
    sevenths that are minor) a related one, and five or six (a semitone or
    major seventh, the tritone) the clash."""
    if not sounding: return "main"
    bass = min(sounding)
    d = fifths_distance(note, bass)
    return "main" if d <= 1 else "related" if d <= 4 else "clash"


IC_ROUGH = {0: 0.0, 1: 1.0, 2: 0.55, 3: 0.2, 4: 0.12, 5: 0.0, 6: 0.85}


def tension(notes):
    """Interval-class roughness of a set of notes, nought (a unison or a
    fifth) to one (a cluster of semitones): the mean over pairs."""
    notes = sorted(set(notes))
    if len(notes) < 2: return 0.0
    vals = []
    for i in range(len(notes)):
        for j in range(i + 1, len(notes)):
            ic = (notes[j] - notes[i]) % 12; ic = min(ic, 12 - ic)
            vals.append(IC_ROUGH[ic])
    return float(np.mean(vals))


def analyse(name):
    meta = json.load(open(os.path.join(BUILD, name + ".notes.json")))
    rate = meta["rate"]
    x = np.fromfile(os.path.join(BUILD, name + ".f32"), dtype=np.float32).reshape(-1, 2)
    fr = audio_frames(x, rate)
    log = voices_log(name)
    lt = np.array([r[0] for r in log])
    split = meta["split"]
    hand_of = (lambda n: 0 if n < split else 1) if split else (lambda n: 0)

    # Each struck note: its curve of level and pitch as the core held it,
    # from the block it was struck in until it fell silent or was struck again.
    onsets = sorted(meta["notes"], key=lambda n: n["t"])
    events = []
    for k, ev in enumerate(onsets):
        layer = hand_of(ev["note"])
        nxt = next((o["t"] for o in onsets[k + 1:] if o["note"] == ev["note"]), meta["length"])
        i0 = int(np.searchsorted(lt, ev["t"])); i1 = int(np.searchsorted(lt, nxt))
        ts, lv, hz, held = [], [], [], []
        for t, _, _, vs in log[i0:i1]:
            mine = [v for v in vs if v[0] == layer and v[1] == ev["note"]]
            if not mine: continue
            v = max(mine, key=lambda v: v[3])
            ts.append(t); lv.append(v[3]); hz.append(v[2]); held.append(v[4])
        if not ts: continue
        ts, lv, hz, held = map(np.array, (ts, lv, hz, held))
        peak = lv.max()
        alive = np.nonzero(lv > 0.02 * max(peak, 1e-6))[0]
        end = ts[alive[-1]] if len(alive) else ts[-1]
        rise = ts[int(np.argmax(lv >= 0.9 * peak))] - ts[0]
        # What else was sounding when it was struck: for its role and the tension.
        t_on = ts[0]
        row = log[min(int(np.searchsorted(lt, t_on + 0.03)), len(log) - 1)][3]
        sounding = [v[1] for v in row if v[3] > 0.05]
        if ev["note"] not in sounding: sounding.append(ev["note"])
        events.append(dict(t0=t_on, t1=end, released=ev["t"] + ev["dur"], note=ev["note"], vel=ev["vel"] / 127,
                           hand=layer, ts=ts, level=lv, hz=hz, held=held, peak=float(peak), rise=float(rise),
                           role=role_of(ev["note"], sounding), tension=tension(sounding)))

    # The level of everything sounding, and the pitch it is centred on, at
    # each analysis frame: brightness is the centroid against that pitch, so
    # a low note's harmonics and a high note's fundamental are not confused.
    f0 = np.full(len(fr["t"]), np.nan)
    for i, t in enumerate(fr["t"]):
        vs = log[min(int(np.searchsorted(lt, t)), len(log) - 1)][3]
        w = np.array([v[3] for v in vs]); h = np.array([v[2] for v in vs])
        if w.sum() > 1e-4: f0[i] = np.exp((w * np.log(h)).sum() / w.sum())
    f0 = np.where(np.isnan(f0), np.nanmedian(f0), f0)
    # In octaves above the pitch, and allowed below nought: the drawbar
    # organ's 16-foot bar puts its centroid under the note it plays.
    fr["bright"] = np.log2(fr["centroid"] / f0)
    # How agitated the playing is: strikes in the last half second (a chord
    # is one strike; four is full), and how fast the spectrum is changing.
    # Unrest weighs least, since a held organ chord's equal-tempered beating
    # moves the spectrum as much as a run does and is heard as a shimmer.
    onset_t = []
    for t0 in sorted(e["t0"] for e in events):
        if not onset_t or t0 - onset_t[-1] > 0.04: onset_t.append(t0)
    onset_t = np.array(onset_t)
    recent = np.array([((onset_t > t - 0.5) & (onset_t <= t)).sum() for t in fr["t"]])
    fr["agitation"] = np.clip(0.75 * recent / 4 + 0.25 * np.clip((fr["unrest"] - 0.08) / 0.3, 0, 1), 0, 1)
    # Noise and grit, nought to one: spectral flatness on a log scale, 0.01
    # (a filtered saw's, a tonal sound's) at nought and 0.3 (most of the way
    # to white noise) at one.
    fr["grain"] = np.clip((np.log10(fr["flatness"]) + 2.0) / 1.5, 0, 1)
    fr["cover"] = np.interp(fr["t"], lt, [r[1] + r[2] for r in log])
    return dict(name=name, meta=meta, frames=fr, events=events, length=meta["length"], split=split)


def summary(a):
    fr = a["frames"]; live = fr["db"] > -50
    return {k: round(float(np.median(fr[k][live])), 3) for k in ("db", "bright", "unrest", "flatness", "agitation", "grain")} | {
        "notes": len(a["events"]), "spread_hz": round(float(np.median(fr["spread"][live])), 1)}


if __name__ == "__main__":
    for n in ("pad", "crossed", "run", "chords"):
        a = analyse(n)
        print(n, summary(a), {r: sum(e["role"] == r for e in a["events"]) for r in ("main", "related", "clash")})
