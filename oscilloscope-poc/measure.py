"""What the scope can say about a frame, beyond the shape of it.

Kept apart from `trigger.py` on purpose: the trigger decides *which* samples
are on screen, and this decides what they amount to. Neither needs the other,
and only this one needs a transform.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

NOTES = ["C", "D♭", "D", "E♭", "E", "F", "G♭", "G", "A♭", "A", "B♭", "B"]

# Harmonics counted into the distortion figure. Eight is where a spec sheet
# usually stops, and past it the bins are mostly noise anyway.
HARMONIC_COUNT = 8

# A line has to stand this far above the average bin to count as a tone.
# Noise is all peaks - the loudest of two hundred random bins clears a
# local-maximum test easily - and a distortion figure for noise is a number
# about nothing.
LINE_OVER_FLOOR_DB = 25.0

# Short of this the answer is the window's own skirt, not the signal's
# distortion. A 397-sample frame - nine milliseconds, which is a perfectly
# ordinary timebase - rounds down to a 256-point transform whose bins are
# 172 Hz apart, and a pure 440 Hz sine read 36% distorted through it. The
# fundamental was not on a bin, so its leakage landed where the harmonics
# were looked for. Callers hand this its own block rather than the displayed
# frame; below the floor it says nothing instead of saying that.
MIN_FFT_SIZE = 1024


def note_for(hz: float | None) -> str | None:
    """The nearest note, and how many cents off it the pitch sits."""
    if not hz or hz < 16 or hz > 12000:
        return None

    midi = 69 + 12 * np.log2(hz / 440.0)
    nearest = int(round(midi))
    cents = int(round((midi - nearest) * 100))
    name = NOTES[nearest % 12] + str(nearest // 12 - 1)
    if cents == 0:
        return name
    return f"{name} {'+' if cents > 0 else '−'}{abs(cents)}"


def dbfs(value: float) -> float:
    """Full scale is 0 dB. Silence is not -inf on a display, it is blank."""
    return -np.inf if value <= 1e-7 else float(20 * np.log10(value))


def estimate_frequency(samples, samplerate: float) -> float | None:
    """Period from level crossings, gated by amplitude so one cycle counts once.

    Cheap, and accurate to a fraction of a percent on anything periodic, which
    is what an oscilloscope is pointed at.  A bare mean-crossing count reads
    double on any waveform that crosses its mean twice a cycle, so a crossing
    only counts once the signal has been properly below the mean since the
    last one.
    """
    x = np.asarray(samples, dtype=np.float64).ravel()
    if x.size < 8:
        return None

    mean = float(x.mean())
    swing = float(max(x.max() - mean, mean - x.min()))
    if swing < 1e-4:
        return None

    arm = mean - 0.25 * swing
    crossings = []
    ready = False

    for i in range(1, x.size):
        if x[i] < arm:
            ready = True
        elif ready and x[i - 1] < mean <= x[i]:
            # Interpolated, so the estimate is not quantised to whole samples.
            step = (mean - x[i - 1]) / (x[i] - x[i - 1])
            crossings.append(i - 1 + step)
            ready = False

    if len(crossings) < 2:
        return None

    # Measured across the whole window rather than pair by pair, so one ragged
    # crossing moves the answer by a fraction of what it otherwise would.
    spread = crossings[-1] - crossings[0]
    return float(samplerate * (len(crossings) - 1) / spread) if spread > 0 else None


@dataclass(frozen=True)
class Harmonics:
    hz: float
    partials: list      # (k, hz, dB relative to the fundamental)
    thd: float


def analyse_harmonics(samples, samplerate: float) -> Harmonics | None:
    """The fundamental, what sits above it, and the distortion that implies.

    Returns ``None`` rather than a number whenever there is no tone to
    measure.  Reported as a ratio, not a verdict: a square wave is 41% and
    there is nothing wrong with it.
    """
    x = np.asarray(samples, dtype=np.float64).ravel()
    size = 1 << int(np.floor(np.log2(max(x.size, 2))))
    if size < MIN_FFT_SIZE:
        return None

    block = x[-size:]
    # Blackman-Harris: sidelobes 92 dB down, so a neighbouring bin is the
    # signal rather than the window's skirt.
    window = np.blackman(size)
    spectrum = np.abs(np.fft.rfft(block * window)) / (size * 0.42 / 2)
    with np.errstate(divide="ignore"):
        db = 20 * np.log10(np.maximum(spectrum, 1e-12))

    bin_hz = samplerate / size
    first = max(2, int(40 / bin_hz))
    last = min(db.size - 1, int(5000 / bin_hz))
    if last <= first:
        return None

    band = db[first : last + 1]
    peak_bin = first + int(np.argmax(band))
    peak = float(db[peak_bin])

    if peak < -70 or peak - float(band.mean()) < LINE_OVER_FLOOR_DB:
        return None

    fundamental = 10 ** (peak / 20)
    partials = []
    distortion = 0.0

    for k in range(1, HARMONIC_COUNT + 1):
        centre = peak_bin * k
        if centre >= db.size - 2:
            break
        near = db[max(1, centre - 2) : min(db.size, centre + 3)]
        level = float(near.max())
        partials.append((k, centre * bin_hz, level - peak))
        if k > 1:
            distortion += (10 ** (level / 20)) ** 2

    return Harmonics(
        hz=peak_bin * bin_hz,
        partials=partials,
        thd=float(np.sqrt(distortion) / fundamental) if fundamental > 0 else 0.0,
    )


@dataclass(frozen=True)
class Reading:
    peak: float
    rms: float
    vpp: float
    hz: float | None
    period_ms: float | None
    note: str | None
    duty: float


def measure(samples, samplerate: float) -> Reading:
    """Everything one channel of one frame has to say."""
    x = np.asarray(samples, dtype=np.float64).ravel()
    if x.size == 0:
        return Reading(0.0, 0.0, 0.0, None, None, None, 0.0)

    hz = estimate_frequency(x, samplerate)
    mean = float(x.mean())

    return Reading(
        peak=float(np.abs(x).max()),
        rms=float(np.sqrt(np.mean(x * x))),
        vpp=float(x.max() - x.min()),
        hz=hz,
        period_ms=1000.0 / hz if hz else None,
        note=note_for(hz),
        duty=float((x > mean).sum()) / x.size * 100.0,
    )
