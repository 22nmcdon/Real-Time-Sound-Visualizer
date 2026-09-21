"""Circular sample buffer shared between the audio thread and the UI thread."""

from __future__ import annotations

import numpy as np


class RingBuffer:
    """Fixed-size circular buffer of multi-channel audio frames.

    There is exactly one writer (the audio callback) and one reader (the
    render timer).  The writer never blocks: it copies its block into the
    backing array and then publishes a new write position.  The reader copies
    out a snapshot and re-reads the write position afterwards; if the region
    it just copied was overwritten mid-read it retries.  That handshake (a
    seqlock) is safe because reading and assigning a Python int attribute is
    atomic under the GIL, so no lock is ever taken on the audio thread.
    """

    def __init__(self, capacity: int, channels: int = 1, dtype=np.float32):
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        if channels <= 0:
            raise ValueError("channels must be positive")
        self._dtype = np.dtype(dtype)
        self._capacity = int(capacity)
        self._channels = int(channels)
        self._buf = np.zeros((self._capacity, self._channels), dtype=self._dtype)
        self._write_pos = 0  # total frames ever written, never wraps
        self._max_read_retries = 8

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def channels(self) -> int:
        return self._channels

    @property
    def dtype(self) -> np.dtype:
        return self._dtype

    @property
    def frames_written(self) -> int:
        """Total frames ever handed to :meth:`write`."""
        return self._write_pos

    def write(self, block) -> None:
        """Append a block of frames.  Called from the audio callback."""
        block = np.asarray(block, dtype=self._dtype)
        if block.ndim == 1:
            block = block.reshape(-1, 1)
        if block.ndim != 2 or block.shape[1] != self._channels:
            raise ValueError(
                f"expected a block of shape (frames, {self._channels}), got {block.shape}"
            )

        if block.shape[0] > self._capacity:
            block = block[-self._capacity :]
        n = block.shape[0]
        if n == 0:
            return

        start = self._write_pos % self._capacity
        end = start + n
        if end <= self._capacity:
            self._buf[start:end] = block
        else:
            split = self._capacity - start
            self._buf[start:] = block[:split]
            self._buf[: n - split] = block[split:]
        self._write_pos += n

    def read_latest(self, n: int) -> np.ndarray:
        """Return the most recent ``n`` frames as a fresh ``(n, channels)`` array.

        The result is zero-padded at the front while the buffer holds fewer
        than ``n`` frames, so callers always get a fixed-size window.  A read
        that keeps losing the race with the writer (only possible when ``n``
        approaches the capacity) returns the torn snapshot rather than
        spinning; at that point the display is the only thing affected.
        """
        if n <= 0:
            raise ValueError("n must be positive")

        out = np.zeros((n, self._channels), dtype=self._dtype)
        for _ in range(self._max_read_retries):
            write_pos = self._write_pos
            count = min(n, write_pos, self._capacity)
            if count:
                start = (write_pos - count) % self._capacity
                end = start + count
                head = n - count  # leading zeros when the buffer is still filling
                if end <= self._capacity:
                    out[head:] = self._buf[start:end]
                else:
                    split = self._capacity - start
                    out[head : head + split] = self._buf[start:]
                    out[head + split :] = self._buf[: count - split]
            # Valid as long as the writer has not lapped the oldest frame we copied.
            if self._write_pos - write_pos <= self._capacity - count:
                break
        return out
