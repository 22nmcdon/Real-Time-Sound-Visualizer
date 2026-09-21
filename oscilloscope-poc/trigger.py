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
    """One frame of every channel, plus what the trigger made of it."""

    channels: list
    triggered: bool
    trigger_index: int | None  # offset of the edge inside the searched buffer
    pre: int                   # samples of the frame that precede the edge
    samplerate: float
    peak: float
    rms: float

    @property
    def samples(self) -> np.ndarray:
        """Channel one, for anything that only wants the one trace."""
        return self.channels[0]

    @property
    def length(self) -> int:
        return self.channels[0].size if self.channels else 0


def find_trigger_index(
    samples,
    level: float,
    edge: str = RISING,
    hysteresis: float = 0.0,
    min_index: int = 1,
    max_index: int | None = None,
    holdoff: int = 0,
) -> int | None:
    """Index of the most recent qualifying edge crossing, or ``None``.

    The *most recent* crossing is chosen so the displayed frame is always the
    freshest one that still has a full window around it -- picking an older
    crossing would add latency between what you hear and what you see.

    ``min_index`` is what makes pre-trigger possible: the caller needs room
    *before* the edge as well as after it, so an edge too near the start of
    the buffer is no use however recent it is.

    ``hysteresis`` mimics a scope's noise rejection: after firing, the signal
    has to travel back past ``level -/+ hysteresis`` before another edge can
    fire, so noise riding on the trigger level cannot produce a burst of
    crossings within one cycle.

    ``holdoff`` is stated as a quiet interval *before* an edge rather than as
    a lockout timer after one.  A bench scope runs the timer because it sweeps
    once per trigger; this re-scans a sliding buffer every frame, and a timer
    anchored to wherever the buffer happens to start would drift a little each
    frame and jitter the trace -- the opposite of what holdoff is for.
    Anchored to the signal it is stable and does the same job: the edge that
    opens a cycle has nothing close behind it and survives, while a second
    crossing mid-cycle does not.  The cost of stating it this way is that a
    holdoff wider than the signal's own period disqualifies every edge there
    is; the page says so rather than letting it read as silence.
    """
    if edge not in EDGES:
        raise ValueError(f"edge must be one of {EDGES}, got {edge!r}")

    x = np.asarray(samples).ravel()
    if x.size < 2:
        return None

    low = max(1, int(min_index))
    high = x.size - 1 if max_index is None else min(int(max_index), x.size - 1)
    if high < low:
        return None

    previous, current = x[:-1], x[1:]
    if edge == RISING:
        crossings = np.flatnonzero((previous < level) & (current >= level)) + 1
        armed = x < level - hysteresis
    else:
        crossings = np.flatnonzero((previous > level) & (current <= level)) + 1
        armed = x > level + hysteresis

    if crossings.size == 0:
        return None

    # Collected across the whole buffer rather than the searchable part of it:
    # both of the rules below need to know about edges outside the window the
    # answer may come from.
    if hysteresis > 0.0:
        # last_armed[i] is the newest index up to i where the signal was past
        # the arming threshold; a crossing only fires if it was armed since
        # the last one fired.  The loop visits candidates, not samples.
        indices = np.arange(x.size)
        last_armed = np.maximum.accumulate(np.where(armed, indices, -1))
        qualified = []
        fired = -1
        for candidate in crossings:
            if last_armed[candidate - 1] > fired:
                fired = int(candidate)
                qualified.append(fired)
        crossings = np.asarray(qualified, dtype=int)
        if crossings.size == 0:
            return None

    if holdoff > 0:
        # The first crossing has no predecessor to measure against; what it
        # has is however much buffer precedes it, and that has to be at least
        # the holdoff or the quiet interval is a guess. Keeping it unchecked
        # was the version of this that was wrong first: with a holdoff wider
        # than the signal's period every other crossing was rejected and the
        # trace locked to whichever edge the buffer happened to open on,
        # which moves every frame. Free running is the honest answer there,
        # and the dock says which setting caused it.
        gaps = np.diff(crossings)
        keep = np.concatenate(([crossings[0] >= holdoff], gaps >= holdoff))
        crossings = crossings[keep]
        if crossings.size == 0:
            return None

    usable = crossings[(crossings >= low) & (crossings <= high)]
    return int(usable[-1]) if usable.size else None


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
        position: float = 0.0,
        holdoff_ms: float = 0.0,
        trigger_source: int = 0,
        search_span: int | None = None,
        min_search_seconds: float = 0.05,
    ):
        self._source = source
        self._position = 0.0
        self._holdoff_ms = 0.0
        self._trigger_source = 0
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
        self.position = position
        self.holdoff_ms = holdoff_ms
        self.trigger_source = trigger_source
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
    def position(self) -> float:
        """How much of the window sits before the edge, as a fraction."""
        return self._position

    @position.setter
    def position(self, value: float) -> None:
        self._position = float(np.clip(float(value), 0.0, 1.0))

    @property
    def holdoff_ms(self) -> float:
        return self._holdoff_ms

    @holdoff_ms.setter
    def holdoff_ms(self, value: float) -> None:
        self._holdoff_ms = max(0.0, float(value))

    @property
    def trigger_source(self) -> int:
        """Which channel the trigger reads.  The frame is cut from all of
        them at that one index, so the channels stay in step."""
        return self._trigger_source

    @trigger_source.setter
    def trigger_source(self, value: int) -> None:
        self._trigger_source = max(0, int(value))

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
        """Grab one frame of every channel, aligned to an edge when there is one.

        The window can start *before* the edge.  ``position`` says how much of
        it does, and the search is bounded at both ends so whichever edge is
        picked has that much room behind it and the rest in front -- no short
        frames, and no padding with silence that was never recorded.  Those
        samples were always in the ring buffer; until this, nothing read them.
        """
        window = self._window_length
        span = self.search_span
        pre = int(round(self._position * window))
        rate = self.samplerate

        channels = self._source.read(window + span)
        if not channels:
            raise RuntimeError("the source returned no channels")

        source = channels[min(self._trigger_source, len(channels) - 1)]
        index = find_trigger_index(
            source,
            level=self._trigger_level,
            edge=self._trigger_edge,
            hysteresis=self._hysteresis,
            min_index=pre,
            max_index=pre + span,
            holdoff=int(round(self._holdoff_ms * rate / 1000.0)),
        )

        total = window + span
        start = total - window if index is None else index - pre
        frames = [channel[start : start + window] for channel in channels]

        wide = frames[0].astype(np.float64, copy=False)
        peak = max(
            float(np.abs(frame).max()) if frame.size else 0.0 for frame in frames
        )
        rms = float(np.sqrt(np.mean(wide * wide))) if wide.size else 0.0

        return TriggerResult(
            channels=frames,
            triggered=index is not None,
            trigger_index=index,
            pre=0 if index is None else pre,
            samplerate=rate,
            peak=peak,
            rms=rms,
        )
