"""The page, driven the way a hand drives it.

Every control here was added because the engine already had the capability
and no way to reach it. A knob that does not move the engine is the same bug
as the missing knob, so each one is pulled once and the engine is asked what
it heard.
"""

import os
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

RATE = 44100


def stereo_source(channels=2, left=440.0, right=660.0):
    """A source with no device behind it, playing something worth looking at."""
    from audio_input import BufferedAudioSource

    class Tone(BufferedAudioSource):
        def __init__(self):
            super().__init__(samplerate=RATE, channels=channels, buffer_seconds=1.0)
            n = RATE // 2
            t = np.arange(n) / RATE
            block = np.zeros((n, channels), dtype=np.float32)
            block[:, 0] = 0.7 * np.sin(2 * np.pi * left * t)
            if channels > 1:
                block[:, 1] = 0.5 * np.sin(2 * np.pi * right * t)
            self.buffer.write(block)

        @property
        def is_running(self):
            return True

        def start(self):
            pass

        def stop(self):
            pass

        def status(self):
            return {
                "device": "Test Tone",
                "samplerate": RATE,
                "channels": channels,
                "blocksize": 512,
                "running": True,
                "overflows": 0,
            }

    return Tone()


class WindowTest(unittest.TestCase):
    app = None

    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication

        cls.app = QApplication.instance() or QApplication([])

    def build(self, channels=2, width=1180, height=760):
        from main_window import MainWindow
        from trigger import TriggerEngine

        source = stereo_source(channels=channels)
        engine = TriggerEngine(source, window_length=882, hysteresis=0.02)
        window = MainWindow(source, engine, fps=60)
        window.resize(width, height)
        window.show()
        self.app.processEvents()
        self.addCleanup(window.close)
        return window, engine


class TheKnobsReachTheEngine(WindowTest):
    def test_every_control_moves_what_it_names(self):
        window, engine = self.build()

        window._position_slider.setValue(25)
        self.assertAlmostEqual(engine.position, 0.25)

        window._holdoff_slider.setValue(3)
        self.assertAlmostEqual(engine.holdoff_ms, 3.0)

        window._window_slider.setValue(10)
        self.assertEqual(engine.window_length, round(10 * RATE / 1000))

        window._level_slider.setValue(250)
        self.assertAlmostEqual(engine.trigger_level, 0.25)

        window._edge_switch.choose(1)
        self.assertEqual(engine.trigger_edge, "falling")

        window._source_switch.choose(1)
        self.assertEqual(engine.trigger_source, 1)

        window._persistence_slider.setValue(4)
        self.assertEqual(window._renderer.persistence, 4)

    def test_a_mono_input_has_no_source_switch(self):
        """A control with one honest position is furniture, not a knob."""
        window, _ = self.build(channels=1)
        self.assertFalse(hasattr(window, "_source_switch"))

    def test_the_pre_trigger_slider_really_buys_a_run_up(self):
        window, engine = self.build()
        window._position_slider.setValue(40)

        result = engine.capture()
        self.assertTrue(result.triggered)
        self.assertEqual(result.pre, round(0.40 * result.length))
        # The run-up is signal, not padding.
        self.assertLess(float(result.samples[: result.pre].min()), -0.3)


class TheTriggerModes(WindowTest):
    def test_single_catches_one_frame_and_stops(self):
        window, _ = self.build()
        window._mode_switch.choose(2)  # single

        for _ in range(8):
            window._on_frame()

        self.assertTrue(window._caught)
        self.assertFalse(window._running)

        # And run re-arms it, rather than resuming a scope that is holding.
        window._on_run_clicked()
        self.assertTrue(window._running)
        self.assertFalse(window._caught)

    def test_normal_holds_rather_than_drawing_an_untriggered_frame(self):
        window, engine = self.build()
        window._mode_switch.choose(1)  # normal

        drawn = []
        window._renderer.update = lambda result: drawn.append(result)

        # A level the signal never reaches: nothing should be drawn at all.
        window._level_slider.setValue(990)
        for _ in range(4):
            window._on_frame()
        self.assertEqual(drawn, [])

        window._level_slider.setValue(0)
        window._on_frame()
        self.assertEqual(len(drawn), 1)


class TheVerdict(WindowTest):
    def test_holdoff_wider_than_the_signal_says_so(self):
        """The picture is the same as silence; the fix is not, so it is named."""
        window, engine = self.build()
        window._holdoff_slider.setValue(10)  # far past a 2.3 ms period

        result = engine.capture()
        self.assertFalse(result.triggered)

        window._write_readout(result, 0.0)
        self.assertIn("far apart", window._verdict.text())

    def test_x_y_on_a_mono_input_says_what_is_missing(self):
        window, engine = self.build(channels=1)
        window._display_switch.choose(1)

        window._write_readout(engine.capture(), 0.0)
        self.assertIn("two channels", window._verdict.text())


class TheStrip(WindowTest):
    def test_the_transport_is_as_tall_as_its_rows(self):
        """Every row of controls is on the page, not clipped behind a scrollbar.

        Measured rather than assumed: a first layout pass reported the strip
        144px shorter than it settled at, the column above banked that, and
        the bottom row of controls was cut in half.
        """
        window, _ = self.build()
        self.app.processEvents()

        self.assertGreaterEqual(
            window._strip.height(),
            window._transport.sizeHint().height(),
            "the transport is taller than the room it was given",
        )

    def test_it_is_capped_rather_than_endless_on_a_narrow_window(self):
        """Eleven stacked controls must not leave the trace a strip."""
        window, _ = self.build(width=430, height=820)
        self.app.processEvents()

        self.assertLessEqual(window._strip.height(), round(820 * 0.5))

    def test_nothing_in_the_frame_refuses_to_be_430_wide(self):
        window, _ = self.build(width=430, height=820)
        self.assertLessEqual(window.minimumSizeHint().width(), 430)
        self.assertEqual(window.width(), 430)


if __name__ == "__main__":
    unittest.main()
