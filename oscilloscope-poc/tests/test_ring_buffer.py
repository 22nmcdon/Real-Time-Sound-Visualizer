"""Ring buffer behaviour, including the writer/reader race it is built for."""

import sys
import threading
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ring_buffer import RingBuffer  # noqa: E402


def ramp(start, stop):
    return np.arange(start, stop, dtype=np.float32)


class RingBufferTest(unittest.TestCase):
    def test_pads_with_zeros_until_full(self):
        buffer = RingBuffer(16)
        buffer.write(ramp(1, 4))
        np.testing.assert_array_equal(
            buffer.read_latest(5).ravel(), [0, 0, 1, 2, 3]
        )

    def test_returns_most_recent_samples(self):
        buffer = RingBuffer(16)
        buffer.write(ramp(0, 20))
        np.testing.assert_array_equal(buffer.read_latest(4).ravel(), [16, 17, 18, 19])

    def test_read_spans_the_wrap_point(self):
        buffer = RingBuffer(10)
        buffer.write(ramp(0, 8))
        buffer.write(ramp(8, 14))  # wraps: capacity 10, 14 frames written
        np.testing.assert_array_equal(
            buffer.read_latest(6).ravel(), [8, 9, 10, 11, 12, 13]
        )

    def test_oversized_write_keeps_the_newest_frames(self):
        buffer = RingBuffer(4)
        buffer.write(ramp(0, 10))
        np.testing.assert_array_equal(buffer.read_latest(4).ravel(), [6, 7, 8, 9])
        self.assertEqual(buffer.frames_written, 4)

    def test_multichannel_round_trip(self):
        buffer = RingBuffer(8, channels=2)
        block = np.array([[1, -1], [2, -2], [3, -3]], dtype=np.float32)
        buffer.write(block)
        np.testing.assert_array_equal(buffer.read_latest(3), block)

    def test_rejects_wrong_channel_count(self):
        buffer = RingBuffer(8, channels=2)
        with self.assertRaises(ValueError):
            buffer.write(np.zeros((4, 3), dtype=np.float32))

    def test_reader_never_sees_a_torn_window(self):
        """Hammer the buffer from a writer thread; every window must be a
        contiguous run of the ramp the writer is producing."""
        buffer = RingBuffer(8192)
        stop = threading.Event()
        failures = []

        def writer():
            position = 0
            while not stop.is_set():
                block = np.arange(position, position + 256, dtype=np.float32)
                buffer.write(block)
                position += 256

        thread = threading.Thread(target=writer, daemon=True)
        thread.start()
        try:
            for _ in range(2000):
                window = buffer.read_latest(1024).ravel()
                fresh = window[window != 0]
                if fresh.size > 1 and not np.all(np.diff(fresh) == 1):
                    failures.append(fresh)
                    break
        finally:
            stop.set()
            thread.join(timeout=2)

        self.assertEqual(failures, [], "reader observed a non-contiguous window")


if __name__ == "__main__":
    unittest.main()
