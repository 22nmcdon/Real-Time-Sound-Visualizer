"""Trigger engine: edge finding, and the stability that makes the trace stand still."""

import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from audio_input import BufferedAudioSource  # noqa: E402
from trigger import FALLING, RISING, TriggerEngine, find_trigger_index  # noqa: E402


class FakeSource(BufferedAudioSource):
    """A source fed by the test instead of by PortAudio.

    It exists to prove the point of the AudioSource split: the trigger engine
    has no idea where its samples come from.
    """

    def __init__(self, samplerate=44100, channels=1, buffer_seconds=1.0):
        super().__init__(samplerate=samplerate, channels=channels,
                         buffer_seconds=buffer_seconds)
        self._running = False

    @property
    def is_running(self):
        return self._running

    def start(self):
        self._running = True

    def stop(self):
        self._running = False

    def feed(self, samples):
        self.buffer.write(np.asarray(samples, dtype=np.float32))


# Largest jump between consecutive samples of the 440 Hz / 0.8 test tone.
SAMPLE_STEP = 0.8 * 2 * np.pi * 440 / 44100


def sine(n, frequency, samplerate, amplitude=0.5, phase=0.0):
    t = np.arange(n, dtype=np.float64) / samplerate
    return (amplitude * np.sin(2 * np.pi * frequency * t + phase)).astype(np.float32)


class FindTriggerIndexTest(unittest.TestCase):
    def test_finds_rising_crossing(self):
        signal = np.array([-1.0, -0.5, 0.5, 1.0], dtype=np.float32)
        self.assertEqual(find_trigger_index(signal, level=0.0, edge=RISING), 2)

    def test_finds_falling_crossing(self):
        signal = np.array([1.0, 0.5, -0.5, -1.0], dtype=np.float32)
        self.assertEqual(find_trigger_index(signal, level=0.0, edge=FALLING), 2)

    def test_picks_the_most_recent_crossing(self):
        """Freshest edge wins, so the display lags the audio as little as possible."""
        signal = sine(1000, frequency=100, samplerate=1000)
        index = find_trigger_index(signal, level=0.0, edge=RISING)
        crossings = np.flatnonzero((signal[:-1] < 0) & (signal[1:] >= 0)) + 1
        self.assertEqual(index, int(crossings[-1]))

    def test_respects_max_index(self):
        signal = sine(1000, frequency=100, samplerate=1000)
        index = find_trigger_index(signal, level=0.0, edge=RISING, max_index=200)
        self.assertIsNotNone(index)
        self.assertLessEqual(index, 200)

    def test_honours_a_non_zero_level(self):
        signal = sine(1000, frequency=10, samplerate=1000, amplitude=1.0)
        index = find_trigger_index(signal, level=0.5, edge=RISING)
        self.assertIsNotNone(index)
        self.assertLess(signal[index - 1], 0.5)
        self.assertGreaterEqual(signal[index], 0.5)

    def test_no_crossing_returns_none(self):
        self.assertIsNone(find_trigger_index(np.zeros(512, dtype=np.float32), level=0.0))
        self.assertIsNone(
            find_trigger_index(sine(512, 50, 1000, amplitude=0.1), level=0.9)
        )

    def test_hysteresis_rejects_noise_riding_on_the_level(self):
        """A chattering edge should fire once, not once per wobble."""
        signal = np.array(
            [-1.0, -1.0, 0.1, -0.05, 0.1, -0.05, 0.1, 1.0, 1.0], dtype=np.float32
        )
        self.assertEqual(find_trigger_index(signal, level=0.0, hysteresis=0.0), 6)
        self.assertEqual(find_trigger_index(signal, level=0.0, hysteresis=0.5), 2)

    def test_hysteresis_still_fires_once_per_real_cycle(self):
        signal = sine(2000, frequency=50, samplerate=1000, amplitude=1.0)
        index = find_trigger_index(signal, level=0.0, hysteresis=0.1)
        crossings = np.flatnonzero((signal[:-1] < 0) & (signal[1:] >= 0)) + 1
        self.assertEqual(index, int(crossings[-1]))

    def test_rejects_unknown_edge(self):
        with self.assertRaises(ValueError):
            find_trigger_index(np.zeros(4, dtype=np.float32), level=0.0, edge="sideways")


class TriggerEngineTest(unittest.TestCase):
    samplerate = 44100

    def make_engine(self, **kwargs):
        source = FakeSource(samplerate=self.samplerate)
        source.start()
        kwargs.setdefault("window_length", 1024)
        return source, TriggerEngine(source, **kwargs)

    def test_window_has_the_requested_length(self):
        source, engine = self.make_engine(window_length=777)
        source.feed(sine(self.samplerate // 2, 440, self.samplerate))
        result = engine.capture()
        self.assertEqual(result.samples.size, 777)

    def test_triggered_window_starts_at_the_trigger_level(self):
        source, engine = self.make_engine(trigger_level=0.25)
        source.feed(sine(self.samplerate // 2, 440, self.samplerate, amplitude=0.8))
        result = engine.capture()
        self.assertTrue(result.triggered)
        # The trigger lands on the first sample past the level, so it can
        # overshoot by up to one sample-step of the waveform (~0.05 here).
        self.assertAlmostEqual(float(result.samples[0]), 0.25, delta=SAMPLE_STEP)
        self.assertGreater(float(result.samples[1]), float(result.samples[0]))

    def test_falling_edge_starts_downwards(self):
        source, engine = self.make_engine(trigger_level=0.25, trigger_edge=FALLING)
        source.feed(sine(self.samplerate // 2, 440, self.samplerate, amplitude=0.8))
        result = engine.capture()
        self.assertTrue(result.triggered)
        self.assertAlmostEqual(float(result.samples[0]), 0.25, delta=SAMPLE_STEP)
        self.assertLess(float(result.samples[1]), float(result.samples[0]))

    def test_steady_tone_produces_a_stable_trace(self):
        """Acceptance criterion 2, offline.

        Feed a continuous 440 Hz tone in ragged blocks -- so each frame sees a
        different phase of the raw buffer -- and check that consecutive
        captured frames are near-identical.  That is exactly what "the
        waveform does not scroll" means.
        """
        source, engine = self.make_engine(window_length=1024, trigger_level=0.0)
        amplitude = 0.6
        phase = 0.0
        step = 2 * np.pi * 440 / self.samplerate
        # An integer-index trigger can only land within one sample of the true
        # crossing, so one sample-step of this tone is the tightest bound any
        # correct implementation can meet.
        tolerance = amplitude * step
        frames = []
        block_sizes = [engine.window_length + engine.search_span]  # prime the buffer
        block_sizes += [1024, 313, 777, 512, 199, 1500, 640, 401]
        for block_size in block_sizes:
            t = phase + step * np.arange(block_size)
            source.feed((amplitude * np.sin(t)).astype(np.float32))
            phase = float(t[-1] + step)
            frames.append(engine.capture())

        self.assertTrue(all(frame.triggered for frame in frames))
        self.assertGreater(len(frames), 8)
        reference = frames[0].samples
        for frame in frames[1:]:
            # Phase lock: every frame opens at the trigger level.
            self.assertLess(abs(float(frame.samples[0])), tolerance)
            # And the whole window overlays the first one.
            drift = float(np.max(np.abs(frame.samples - reference)))
            self.assertLess(drift, tolerance, "trace drifted between frames")

    def test_untriggered_frames_fall_back_to_the_latest_window(self):
        """Silence must keep the display live rather than freezing it."""
        source, engine = self.make_engine(trigger_level=0.9)
        source.feed(sine(self.samplerate // 2, 440, self.samplerate, amplitude=0.2))
        result = engine.capture()
        self.assertFalse(result.triggered)
        self.assertIsNone(result.trigger_index)
        expected = source.get_latest_window(engine.window_length)
        np.testing.assert_allclose(result.samples, expected, atol=1e-6)

    def test_reports_peak_and_rms(self):
        source, engine = self.make_engine()
        source.feed(sine(self.samplerate // 2, 440, self.samplerate, amplitude=0.5))
        result = engine.capture()
        self.assertAlmostEqual(result.peak, 0.5, delta=0.01)
        self.assertAlmostEqual(result.rms, 0.5 / np.sqrt(2), delta=0.01)

    def test_settings_change_at_runtime(self):
        source, engine = self.make_engine()
        engine.trigger_edge = "FALLING"
        self.assertEqual(engine.trigger_edge, FALLING)
        with self.assertRaises(ValueError):
            engine.trigger_edge = "diagonal"
        engine.window_length = 1  # clamped up to the floor
        self.assertGreaterEqual(engine.window_length, 64)
        engine.window_length = 10 ** 9  # clamped down to one second
        self.assertLessEqual(engine.window_length, self.samplerate)
        engine.hysteresis = -5
        self.assertEqual(engine.hysteresis, 0.0)

    def test_window_plus_search_span_fits_the_ring_buffer(self):
        """The engine must never ask the source for more than it can hold."""
        source, engine = self.make_engine()
        engine.window_length = 10 ** 9
        self.assertLessEqual(
            engine.window_length + engine.search_span, source.buffer.capacity
        )

    def test_stereo_source_is_downmixed(self):
        source = FakeSource(samplerate=self.samplerate, channels=2)
        source.start()
        block = np.zeros((1024, 2), dtype=np.float32)
        block[:, 0] = 1.0
        block[:, 1] = -0.5
        source.feed(block)
        window = source.get_latest_window(512)
        self.assertEqual(window.shape, (512,))
        np.testing.assert_allclose(window, 0.25, atol=1e-6)


if __name__ == "__main__":
    unittest.main()


class PreTriggerTest(unittest.TestCase):
    """The window can start before the edge, which is what pre-trigger is."""

    samplerate = 44100

    def source_with_tone(self, frequency=440, amplitude=0.6):
        source = FakeSource(samplerate=self.samplerate, buffer_seconds=1.0)
        source.start()
        source.feed(sine(self.samplerate // 2, frequency, self.samplerate, amplitude))
        return source

    def test_position_puts_the_edge_inside_the_window(self):
        source = self.source_with_tone()
        engine = TriggerEngine(source, window_length=1024, trigger_level=0.0)

        for position in (0.0, 0.25, 0.5, 0.9):
            engine.position = position
            result = engine.capture()

            self.assertTrue(result.triggered, f"no trigger at position {position}")
            self.assertEqual(result.samples.size, 1024)
            self.assertEqual(result.pre, round(position * 1024))

            # The sample at the trigger point is the one on the level; what
            # sits before it is the run-up, which is the whole point.
            self.assertAlmostEqual(float(result.samples[result.pre]), 0.0, delta=SAMPLE_STEP)

    def test_the_run_up_is_real_signal_not_padding(self):
        """Half a window before a rising zero crossing of a sine is the
        negative half of the cycle, not silence."""
        source = self.source_with_tone()
        engine = TriggerEngine(source, window_length=512, trigger_level=0.0)
        engine.position = 0.5
        result = engine.capture()

        before = result.samples[: result.pre]
        self.assertGreater(before.size, 0)
        self.assertLess(float(before.min()), -0.3, "the run-up is flat")

    def test_holdoff_rejects_an_edge_with_one_close_behind_it(self):
        """A wave that crosses the level twice a cycle should settle on the
        crossing that opens the cycle once holdoff is wider than the gap."""
        # Two rising zero crossings per 100-sample cycle: the big one that
        # opens it, at sample 20, and the recovery from a mid-cycle dip, at
        # sample 52.  The gap between them is 32 samples; the gap between a
        # recovery and the next cycle's opening edge is 68.
        cycle = np.concatenate([
            np.linspace(-1, 1, 40),
            np.linspace(1, -0.2, 10),
            np.linspace(-0.2, 1, 10),
            np.linspace(1, -1, 40),
        ]).astype(np.float32)
        signal = np.tile(cycle, 12)

        loose = find_trigger_index(signal, 0.0, RISING, hysteresis=0.0, holdoff=0)
        # Wider than 32 and narrower than 68: rejects the recovery, keeps the
        # opening edge.
        tight = find_trigger_index(signal, 0.0, RISING, hysteresis=0.0, holdoff=40)

        self.assertEqual(loose, 1152, "the freshest edge is the little recovery")
        self.assertEqual(tight, 1120, "holdoff should fall back to the cycle's own edge")

    def test_holdoff_narrower_than_the_gap_rejects_nothing(self):
        """Holdoff is a quiet interval, not a blanket delay: an edge with
        enough silence behind it survives however busy the rest is."""
        cycle = np.concatenate([
            np.linspace(-1, 1, 40),
            np.linspace(1, -0.2, 10),
            np.linspace(-0.2, 1, 10),
            np.linspace(1, -1, 40),
        ]).astype(np.float32)
        signal = np.tile(cycle, 12)

        self.assertEqual(
            find_trigger_index(signal, 0.0, RISING, hysteresis=0.0, holdoff=30),
            find_trigger_index(signal, 0.0, RISING, hysteresis=0.0, holdoff=0),
        )

    def test_min_index_refuses_an_edge_with_no_room_behind_it(self):
        signal = sine(2000, 50, 1000, amplitude=1.0)
        early = find_trigger_index(signal, 0.0, RISING, hysteresis=0.0, max_index=400)
        self.assertIsNotNone(early)
        self.assertLessEqual(early, 400)

        # Ask for room before it and the same search has to look further in.
        later = find_trigger_index(
            signal, 0.0, RISING, hysteresis=0.0, min_index=500, max_index=900
        )
        self.assertIsNotNone(later)
        self.assertGreaterEqual(later, 500)


class StereoTest(unittest.TestCase):
    """Two channels, cut at one index, so they stay in step."""

    samplerate = 44100

    def test_both_channels_come_back_and_are_the_same_length(self):
        source = FakeSource(samplerate=self.samplerate, channels=2, buffer_seconds=1.0)
        source.start()

        block = np.zeros((self.samplerate // 2, 2), dtype=np.float32)
        block[:, 0] = sine(block.shape[0], 440, self.samplerate, 0.6)
        block[:, 1] = sine(block.shape[0], 440, self.samplerate, 0.3)
        source.feed(block)

        engine = TriggerEngine(source, window_length=1024)
        result = engine.capture()

        self.assertEqual(len(result.channels), 2)
        self.assertEqual(result.channels[0].size, result.channels[1].size)
        # Same wave at half the level: the frames must be aligned in time,
        # not merely the same length.
        np.testing.assert_allclose(
            result.channels[0], result.channels[1] * 2, atol=0.02
        )

    def test_the_trigger_source_chooses_which_channel_is_read(self):
        source = FakeSource(samplerate=self.samplerate, channels=2, buffer_seconds=1.0)
        source.start()

        block = np.zeros((self.samplerate // 2, 2), dtype=np.float32)
        block[:, 0] = 0.05 * np.random.default_rng(0).normal(size=block.shape[0])
        block[:, 1] = sine(block.shape[0], 440, self.samplerate, 0.8)
        source.feed(block)

        engine = TriggerEngine(source, window_length=1024, trigger_level=0.4)
        engine.trigger_source = 1
        result = engine.capture()

        self.assertTrue(result.triggered)
        # The frame is cut on channel two's edge, so that is the channel
        # sitting on the level at the trigger point.
        self.assertAlmostEqual(float(result.channels[1][result.pre]), 0.4, delta=0.07)
