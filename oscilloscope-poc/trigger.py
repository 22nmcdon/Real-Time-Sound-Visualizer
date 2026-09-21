"""Level trigger: turns a free-running stream into a stable, repeatable trace.

Without this, every frame starts at an arbitrary phase and the waveform
appears to scroll.  With it, every frame starts at the same point of the
waveform and the trace stands still, exactly like an analog scope.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

RISING = "rising"
FALLING = "falling"
EDGES = (RISING, FALLING)

# Bounds that keep a window plus its search span comfortably inside the
# source's ring buffer no matter what the UI asks for.
MIN_WINDOW = 64
MAX_WINDOW_SECONDS = 1.0
MAX_SEARCH_SECONDS = 0.25


@dataclass(frozen=True)
class TriggerResult:
    """One frame's worth of samples plus what the trigger made of them."""

    samples: np.ndarray
    triggered: bool
    trigger_index: int | None  # offset of the edge inside the searched buffer
    peak: float
    rms: float


def find_trigger_index(
    samples,
    level: float,
    edge: str = RISING,
    hysteresis: float = 0.0,
    max_index: int | None = None,
) -> int | None:
    """Index of the most recent qualifying edge crossing, or ``None``.

    The *most recent* crossing is chosen so the displayed frame is always the
    freshest one that still has a full window behind it -- picking an older
    crossing would add latency between what you hear and what you see.

    ``hysteresis`` mimics a scope's noise rejection: after firing, the signal
    has to travel back past ``level -/+ hysteresis`` before another edge can
    fire, so noise riding on the trigger level cannot produce a burst of
    crossings within one cycle.
    """
    if edge not in EDGES:
        raise ValueError(f"edge must be one of {EDGES}, got {edge!r}")

    x = np.asarray(samples).ravel()
    if x.size < 2:
        return None

    limit = x.size - 1 if max_index is None else min(int(max_index), x.size - 1)
    if limit < 1:
        return None

    previous, current = x[:-1], x[1:]
    if edge == RISING:
        crossings = np.flatnonzero((previous < level) & (current >= level)) + 1
        armed = x < level - hysteresis
    else:
        crossings = np.flatnonzero((previous > level) & (current <= level)) + 1
        armed = x > level + hysteresis

    crossings = crossings[crossings <= limit]
    if crossings.size == 0:
        return None
    if hysteresis <= 0.0:
        return int(crossings[-1])

    # last_armed[i] is the newest index up to i where the signal was past the
    # arming threshold; a crossing only fires if it was armed since the last
    # one fired.  The loop only visits candidate crossings, not samples.
    indices = np.arange(x.size)
    last_armed = np.maximum.accumulate(np.where(armed, indices, -1))
    fired = -1
    for candidate in crossings:
        if last_armed[candidate - 1] > fired:
            fired = int(candidate)
    return fired if fired >= 0 else None


class TriggerEngine:
    """Pulls a window from an :class:`~audio_input.AudioSource` and aligns it.

    The engine asks the source for ``window_length + search_span`` samples and
    looks for an edge inside the first ``search_span`` of them, which
    guarantees a full window exists after whichever edge it picks -- no
    padding or short frames.  When nothing qualifies (silence, a
    non-periodic signal, a trigger level the signal never reaches) it falls
    back to the most recent window so the display keeps running instead of
    freezing.
    """

    def __init__(
        self,
        source,
        window_length: int = 1024,
        trigger_level: float = 0.0,
        trigger_edge: str = RISING,
        hysteresis: float = 0.02,
        search_span: int | None = None,
        min_search_seconds: float = 0.05,
    ):
        self._source = source
        self._trigger_level = 0.0
        self._trigger_edge = RISING
        self._hysteresis = 0.0
        self._window_length = MIN_WINDOW
        self._search_span = None
        self._min_search_seconds = float(min_search_seconds)

        self.window_length = window_length
        self.trigger_level = trigger_level
        self.trigger_edge = trigger_edge
        self.hysteresis = hysteresis
        if search_span is not None:
            self.search_span = search_span

    @property
    def source(self):
        return self._source

    @property
    def samplerate(self) -> float:
        return float(self._source.samplerate)

    @property
    def window_length(self) -> int:
        return self._window_length

    @window_length.setter
    def window_length(self, value: int) -> None:
        # Half the buffer at most, so there is always room for a search span.
        upper = max(
            MIN_WINDOW,
            min(int(MAX_WINDOW_SECONDS * self.samplerate), self._capacity // 2),
        )
        self._window_length = int(np.clip(int(value), MIN_WINDOW, upper))

    @property
    def trigger_level(self) -> float:
        return self._trigger_level

    @trigger_level.setter
    def trigger_level(self, value: float) -> None:
        self._trigger_level = float(value)

    @property
    def trigger_edge(self) -> str:
        return self._trigger_edge

    @trigger_edge.setter
    def trigger_edge(self, value: str) -> None:
        value = str(value).lower()
        if value not in EDGES:
            raise ValueError(f"trigger_edge must be one of {EDGES}, got {value!r}")
        self._trigger_edge = value

    @property
    def hysteresis(self) -> float:
        return self._hysteresis

    @hysteresis.setter
    def hysteresis(self, value: float) -> None:
        self._hysteresis = max(0.0, float(value))

    @property
    def _capacity(self) -> int:
        """How many samples the source can hand back in one go."""
        return int(self._source.capacity)

    @property
    def search_span(self) -> int:
        """How far back an edge may be found, in samples."""
        if self._search_span is None:
            span = max(
                self._window_length, int(self._min_search_seconds * self.samplerate)
            )
            span = min(span, int(MAX_SEARCH_SECONDS * self.samplerate))
        else:
            span = self._search_span
        # Never ask the source for more than it holds: past that the buffer
        # pads with zeros, which would fake an edge that is not in the signal.
        return max(1, min(span, self._capacity - self._window_length))

    @search_span.setter
    def search_span(self, value: int | None) -> None:
        if value is None:
            self._search_span = None
            return
        upper = max(1, int(MAX_SEARCH_SECONDS * self.samplerate))
        self._search_span = int(np.clip(int(value), 1, upper))

    def capture(self) -> TriggerResult:
        """Grab one frame, aligned to a trigger edge when there is one."""
        window = self._window_length
        span = self.search_span
        buffer = self._source.get_latest_window(window + span)

        index = find_trigger_index(
            buffer,
            level=self._trigger_level,
            edge=self._trigger_edge,
            hysteresis=self._hysteresis,
            max_index=span,
        )
        if index is None:
            samples = buffer[-window:]
        else:
            samples = buffer[index : index + window]

        wide = samples.astype(np.float64, copy=False)
        peak = float(np.abs(wide).max()) if wide.size else 0.0
        rms = float(np.sqrt(np.mean(wide * wide))) if wide.size else 0.0
        return TriggerResult(
            samples=samples,
            triggered=index is not None,
            trigger_index=index,
            peak=peak,
            rms=rms,
        )
