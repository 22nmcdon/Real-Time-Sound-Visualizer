"""Audio sources.  The scope consumes this interface, not a microphone.

`AudioSource` is deliberately narrow so a later phase can drop in a file
player (or a signal generator) without the trigger engine or the renderer
knowing the difference.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from ring_buffer import RingBuffer

DEFAULT_SAMPLERATE = 44100
DEFAULT_BLOCKSIZE = 512
DEFAULT_BUFFER_SECONDS = 4.0

_sounddevice = None


def sd():
    """Import ``sounddevice`` on first use.

    Importing it loads PortAudio, which fails on machines with no audio
    stack.  Deferring the import keeps the rest of the pipeline (and its
    tests) usable there, and lets the caller report a clean error.
    """
    global _sounddevice
    if _sounddevice is None:
        import sounddevice

        _sounddevice = sounddevice
    return _sounddevice


class AudioSource(ABC):
    """Anything that can hand the scope its most recent samples."""

    @property
    @abstractmethod
    def samplerate(self) -> float:
        ...

    @property
    @abstractmethod
    def channels(self) -> int:
        ...

    @property
    @abstractmethod
    def is_running(self) -> bool:
        ...

    @property
    @abstractmethod
    def capacity(self) -> int:
        """Most samples this source can serve in one window."""

    @abstractmethod
    def start(self) -> None:
        ...

    @abstractmethod
    def stop(self) -> None:
        ...

    @abstractmethod
    def read(self, n_samples: int) -> list:
        """Most recent ``n_samples`` of every channel.

        One float32 array per channel, each exactly ``n_samples`` long. The
        scope reads this; `get_latest_window` below is the mono convenience
        on top of it, for anything that only wants one trace.
        """

    def get_latest_window(self, n_samples: int) -> np.ndarray:
        """The same window, downmixed to one channel."""
        channels = self.read(n_samples)
        if len(channels) == 1:
            return channels[0]
        return np.mean(channels, axis=0, dtype=np.float32)

    def status(self) -> dict:
        """Free-form diagnostics for the UI status line."""
        return {}

    def __enter__(self) -> "AudioSource":
        self.start()
        return self

    def __exit__(self, *exc_info) -> None:
        self.stop()


class BufferedAudioSource(AudioSource):
    """Base for sources that push blocks into a :class:`RingBuffer`.

    Subclasses fill the buffer from wherever their audio comes from -- a
    PortAudio callback here, a playback thread reading a file later -- and
    inherit the whole consumer side.
    """

    def __init__(
        self,
        samplerate: float = DEFAULT_SAMPLERATE,
        channels: int = 1,
        buffer_seconds: float = DEFAULT_BUFFER_SECONDS,
        channel: int | None = None,
    ):
        if channel is not None and not 0 <= channel < channels:
            raise ValueError(f"channel {channel} outside 0..{channels - 1}")
        self._samplerate = float(samplerate)
        self._channels = int(channels)
        self._channel = channel
        capacity = max(1024, int(buffer_seconds * self._samplerate))
        self._buffer = RingBuffer(capacity, self._channels, dtype=np.float32)

    @property
    def samplerate(self) -> float:
        return self._samplerate

    @property
    def channels(self) -> int:
        return self._channels

    @property
    def buffer(self) -> RingBuffer:
        return self._buffer

    @property
    def capacity(self) -> int:
        return self._buffer.capacity

    @property
    def frames_captured(self) -> int:
        return self._buffer.frames_written

    def read(self, n_samples: int) -> list:
        """Every channel of the most recent ``n_samples``.

        One fresh array per channel, so the caller can hold onto them while
        the audio thread keeps writing.  A single-channel source answers with
        a list of one rather than with a bare array: the consumer should not
        have to ask how many channels there are before it can read.
        """
        frames = self._buffer.read_latest(n_samples)

        if self._channel is not None:
            return [np.ascontiguousarray(frames[:, self._channel])]

        return [np.ascontiguousarray(frames[:, i]) for i in range(self._channels)]


class MicrophoneInput(BufferedAudioSource):
    """Live capture from an input device via PortAudio."""

    def __init__(
        self,
        samplerate: float | None = DEFAULT_SAMPLERATE,
        channels: int = 1,
        blocksize: int = DEFAULT_BLOCKSIZE,
        device=None,
        buffer_seconds: float = DEFAULT_BUFFER_SECONDS,
        channel: int | None = None,
    ):
        if samplerate is None:
            samplerate = device_default_samplerate(device)
        super().__init__(
            samplerate=samplerate,
            channels=channels,
            buffer_seconds=buffer_seconds,
            channel=channel,
        )
        self._blocksize = int(blocksize)
        self._device = device
        self._stream = None
        self.overflow_count = 0
        self.last_status = ""

    @property
    def device(self):
        return self._device

    @property
    def blocksize(self) -> int:
        return self._blocksize

    @property
    def is_running(self) -> bool:
        return self._stream is not None and self._stream.active

    @property
    def device_name(self) -> str:
        try:
            info = sd().query_devices(self._device, "input")
        except Exception:  # device gone, or no PortAudio at all
            return "unknown"
        return str(info.get("name", "unknown"))

    def start(self) -> None:
        if self._stream is not None:
            return
        stream = sd().InputStream(
            samplerate=self._samplerate,
            blocksize=self._blocksize,
            channels=self._channels,
            dtype="float32",
            device=self._device,
            callback=self._callback,
        )
        stream.start()
        self._stream = stream
        # PortAudio may hand back a rate the device actually supports.
        self._samplerate = float(stream.samplerate)

    def stop(self) -> None:
        stream, self._stream = self._stream, None
        if stream is not None:
            stream.stop()
            stream.close()

    def _callback(self, indata, frames, time_info, status) -> None:
        """PortAudio thread.  Copy and return -- no allocation, no locks."""
        if status:
            if status.input_overflow:
                self.overflow_count += 1
            self.last_status = str(status)
        self._buffer.write(indata)

    def status(self) -> dict:
        return {
            "device": self.device_name,
            "samplerate": self._samplerate,
            "channels": self._channels,
            "blocksize": self._blocksize,
            "frames": self.frames_captured,
            "overflows": self.overflow_count,
            "running": self.is_running,
        }


def device_default_samplerate(device=None) -> float:
    """Preferred sample rate of an input device, falling back to 44100 Hz."""
    try:
        info = sd().query_devices(device, "input")
        return float(info["default_samplerate"])
    except Exception:
        return float(DEFAULT_SAMPLERATE)


def describe_devices() -> str:
    """Human-readable device table for ``main.py --list-devices``."""
    return str(sd().query_devices())
