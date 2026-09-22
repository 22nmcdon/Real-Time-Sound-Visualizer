"""Audio the browser tests need, made rather than stored.

Committing a few megabytes of WAV to carry a handful of sine waves would be
silly, and a fixture you can read the source of is easier to reason about than
one you have to open in an editor. Everything here is deterministic.
"""
import math, os, struct, wave

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "fixtures")
RATE = 44100


def write(name, seconds, channels, fn):
    """`fn(t, channel)` in [-1, 1], written as 16-bit PCM."""
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name)
    frames = int(seconds * RATE)
    data = bytearray()
    for i in range(frames):
        t = i / RATE
        for c in range(channels):
            v = max(-1.0, min(1.0, fn(t, c)))
            data += struct.pack("<h", int(v * 32767))
    with wave.open(path, "wb") as w:
        w.setnchannels(channels); w.setsampwidth(2); w.setframerate(RATE)
        w.writeframes(bytes(data))
    return path


def fade(t, seconds, edge=0.01):
    """Silence at both ends, so a loop does not click."""
    return min(1.0, t / edge, max(0.0, (seconds - t)) / edge)


def build():
    made = []
    # A perfect fifth, one tone per channel: the X-Y figure is a known shape.
    made.append(write("test-fifth.wav", 2.0, 2,
                      lambda t, c: 0.5 * fade(t, 2.0)
                      * math.sin(2 * math.pi * (330 if c else 220) * t)))

    # Four "stems" that land in four different bands, so the band split and the
    # lane colours have something to separate. Not music, and not pretending.
    def drums(t, c):
        beat = t % 0.5
        return 0.6 * math.exp(-beat * 30) * math.sin(2 * math.pi * 60 * beat)

    def bass(t, c):
        return 0.5 * math.sin(2 * math.pi * 110 * t)

    def other(t, c):
        return 0.3 * (math.sin(2 * math.pi * 1400 * t)
                      + 0.5 * math.sin(2 * math.pi * 2100 * t))

    def vocals(t, c):
        wobble = 1 + 0.02 * math.sin(2 * math.pi * 5 * t)
        return 0.4 * math.sin(2 * math.pi * 520 * wobble * t)

    for name, fn in (("drums", drums), ("bass", bass),
                     ("other", other), ("vocals", vocals)):
        made.append(write(name + ".wav", 2.0, 2,
                          lambda t, c, fn=fn: fn(t, c) * fade(t, 2.0)))
    return made


def ensure():
    """Build only what is missing, so repeated test runs stay quick."""
    needed = ["test-fifth.wav", "drums.wav", "bass.wav", "other.wav", "vocals.wav"]
    if all(os.path.exists(os.path.join(OUT, n)) for n in needed):
        return OUT
    build()
    return OUT


if __name__ == "__main__":
    for p in build():
        print("wrote", p)
