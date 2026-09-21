"""What the frame measures, checked against signals whose answers are known.

The interesting cases here are all the same shape: a number that is confidently
wrong is worse than no number, so most of these assert that the reading is
withheld rather than that it is right.
"""

import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import measure  # noqa: E402

RATE = 44100


def tone(hz, samples, amplitude=1.0):
    t = np.arange(samples) / RATE
    return (amplitude * np.sin(2 * np.pi * hz * t)).astype(np.float32)


class Pitch(unittest.TestCase):
    def test_a_sine_reads_its_own_frequency_and_note(self):
        reading = measure.measure(tone(440.0, 4410), RATE)
        self.assertIsNotNone(reading.hz)
        self.assertAlmostEqual(reading.hz, 440.0, delta=1.0)
        self.assertEqual(reading.note, "A4")
        self.assertAlmostEqual(reading.vpp, 2.0, delta=0.01)

    def test_silence_has_no_pitch(self):
        reading = measure.measure(np.zeros(4410, dtype=np.float32), RATE)
        self.assertIsNone(reading.hz)
        self.assertIsNone(reading.note)


class Distortion(unittest.TestCase):
    def test_a_clean_sine_is_not_distorted(self):
        harmonics = measure.analyse_harmonics(tone(440.0, 8192), RATE)
        self.assertIsNotNone(harmonics)
        self.assertLess(harmonics.thd, 0.01)

    def test_a_square_wave_is_about_forty_percent(self):
        """A square is 43% by construction, and that is not a fault."""
        square = np.sign(tone(440.0, 8192)).astype(np.float32)
        harmonics = measure.analyse_harmonics(square, RATE)
        self.assertIsNotNone(harmonics)
        self.assertGreater(harmonics.thd, 0.3)
        self.assertLess(harmonics.thd, 0.5)

    def test_noise_has_no_fundamental_to_be_distorted_from(self):
        noise = np.random.default_rng(0).normal(0, 0.2, 8192).astype(np.float32)
        self.assertIsNone(measure.analyse_harmonics(noise, RATE))

    def test_a_block_too_short_to_resolve_says_nothing(self):
        """The regression this floor exists for.

        397 samples - nine milliseconds, an ordinary timebase - rounds down to
        a 256-point transform whose bins are 172 Hz apart. A pure 440 Hz sine
        read 36% distorted through it, because the fundamental was not on a
        bin and its leakage landed where the harmonics were looked for.
        """
        self.assertIsNone(measure.analyse_harmonics(tone(440.0, 397), RATE))
        self.assertGreaterEqual(measure.MIN_FFT_SIZE, 512)


if __name__ == "__main__":
    unittest.main()
