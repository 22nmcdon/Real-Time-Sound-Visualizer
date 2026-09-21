"""The screen, which has two displays and one plot.

Nothing here looks at pixels. What it checks is which curves are on the plot
and what shape the stage is, because those are the decisions the renderer
makes and a screenshot would only restate them.
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


def frame(hz, samples=882, amplitude=0.7):
    t = np.arange(samples) / RATE
    return (amplitude * np.sin(2 * np.pi * hz * t)).astype(np.float32)


class Capture:
    """Stands in for a `TriggerResult`, which is all the renderer reads."""

    def __init__(self, channels, triggered=True, pre=0):
        self.channels = channels
        self.triggered = triggered
        self.pre = pre


class RendererTest(unittest.TestCase):
    app = None

    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication

        cls.app = QApplication.instance() or QApplication([])

    def build(self):
        from renderer import ScopeRenderer

        return ScopeRenderer(samplerate=RATE)


class Traces(RendererTest):
    def test_one_channel_draws_one_trace(self):
        scope = self.build()
        scope.update(Capture([frame(440)]))
        self.assertTrue(scope._curves[0].isVisible())
        self.assertFalse(scope._curves[1].isVisible())

    def test_two_channels_draw_two(self):
        scope = self.build()
        scope.update(Capture([frame(440), frame(660, amplitude=0.5)]))
        self.assertTrue(scope._curves[0].isVisible())
        self.assertTrue(scope._curves[1].isVisible())

    def test_the_run_up_marker_appears_only_when_there_is_a_run_up(self):
        scope = self.build()

        scope.update(Capture([frame(440)], pre=0))
        self.assertFalse(scope._position_line.isVisible())

        scope.update(Capture([frame(440)], pre=200))
        self.assertTrue(scope._position_line.isVisible())


class Displays(RendererTest):
    def test_x_y_squares_the_stage_and_y_t_lets_it_go(self):
        """A circle that is not round is a phase reading that is wrong."""
        from renderer import UNCONSTRAINED, XY, YT

        scope = self.build()
        scope.widget.resize(900, 300)

        scope.mode = XY
        self.assertEqual(scope._view.maximumWidth(), scope.widget.height())

        scope.mode = YT
        self.assertEqual(scope._view.maximumWidth(), UNCONSTRAINED)

    def test_x_y_needs_two_channels_and_draws_nothing_without_them(self):
        from renderer import XY

        scope = self.build()
        scope.mode = XY

        scope.update(Capture([frame(440)]))
        self.assertFalse(scope._curves[0].isVisible())

        scope.update(Capture([frame(440), frame(660)]))
        self.assertTrue(scope._curves[0].isVisible())

    def test_an_unknown_display_is_refused_rather_than_ignored(self):
        scope = self.build()
        with self.assertRaises(ValueError):
            scope.mode = "polar"


class Persistence(RendererTest):
    def test_ghosts_appear_with_depth_and_leave_with_it(self):
        scope = self.build()
        scope.persistence = 3

        for _ in range(5):
            scope.update(Capture([frame(440)]))
        self.assertEqual(sum(g.isVisible() for g in scope._ghosts), 3)

        scope.persistence = 0
        scope.update(Capture([frame(440)]))
        self.assertEqual(sum(g.isVisible() for g in scope._ghosts), 0)

    def test_depth_is_clamped_to_what_there_are_curves_for(self):
        from renderer import MAX_PERSISTENCE

        scope = self.build()
        scope.persistence = 99
        self.assertEqual(scope.persistence, MAX_PERSISTENCE)

    def test_a_ghost_keeps_its_own_copy_of_the_frame(self):
        """The ring buffer under a captured frame is written over; a ghost
        that held a view of it would redraw as whatever arrived next."""
        scope = self.build()
        scope.persistence = 2

        first = frame(440)
        scope.update(Capture([first]))
        scope.update(Capture([frame(880)]))

        kept = scope._history[0][1]
        first[:] = 0.0
        self.assertGreater(float(np.abs(kept).max()), 0.5)


if __name__ == "__main__":
    unittest.main()
