"""The house style, as checks rather than as good intentions.

`BRANDING.md` ends with a checklist. Three of its lines are things a machine
can settle, and all three are things that were got wrong here first:

- no hard-coded hex where a token exists
- checked at 430px wide, not only at 1200px
- anything that reserves height reserves it always
"""

import os
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Before Qt is imported by anything: these run on a machine with no display.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# The surfaces that must name no colour of their own. `branding.py` is the one
# place a hex digit is allowed, which is what makes a second light a dict swap.
PAINTED = ("renderer.py", "main_window.py", "main.py")

HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")
RGBA = re.compile(r"\brgba?\s*\(")


class NoLooseColour(unittest.TestCase):
    def test_only_branding_names_a_colour(self):
        """No hard-coded hex or rgba() where a token exists.

        A whole-line comment is skipped and nothing else is - deliberately
        not "strip everything after the first #", which would take the hex
        out of `TRACE = "#3dff7a"` and pass the very line this is looking
        for. The cost is that a hex written in a trailing comment fails the
        check; the answer to that is not to write one.
        """
        for name in PAINTED:
            for number, line in enumerate((ROOT / name).read_text().splitlines(), 1):
                if line.lstrip().startswith("#"):
                    continue

                where = f"{name}:{number}"
                self.assertIsNone(
                    HEX.search(line),
                    f"{where}: a literal colour will not follow the light -> {line.strip()}",
                )
                self.assertIsNone(
                    RGBA.search(line),
                    f"{where}: an rgba() will not follow the light -> {line.strip()}",
                )

    def test_branding_still_holds_the_five_that_never_move(self):
        import branding as house

        for token in ("SAGE", "APPROACH", "ENCLOSURE", "RUST", "UNRESOLVED"):
            self.assertTrue(
                getattr(house, token).startswith("#"),
                f"{token} is one of the five and has to stay a colour",
            )


def qt_available():
    """Whether there is a Qt to open a window with at all.

    The rest of the suite needs neither a display nor a sound card, and that
    stays true - this is the one file that does, and it skips rather than
    failing where it cannot run.
    """
    try:
        import importlib

        importlib.import_module("PyQt6.QtWidgets")
        importlib.import_module("pyqtgraph")
    except Exception:
        return False
    return True


@unittest.skipUnless(qt_available(), "PyQt6 and pyqtgraph are not installed")
class TheFrame(unittest.TestCase):
    """Opens the real window against a source that answers without a device."""

    app = None

    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication

        cls.app = QApplication.instance() or QApplication([])

    def build(self, width, height):
        from audio_input import BufferedAudioSource
        from main_window import MainWindow
        from trigger import TriggerEngine

        class Silent(BufferedAudioSource):
            """A source with no device behind it - the frame does not care."""

            def __init__(self):
                super().__init__(samplerate=44100, channels=1, buffer_seconds=1.0)

            @property
            def is_running(self):
                return True

            def start(self):
                pass

            def stop(self):
                pass

            def status(self):
                return {
                    "device": "A Rather Long Audio Interface Name",
                    "samplerate": 44100,
                    "channels": 1,
                    "blocksize": 512,
                    "running": True,
                    "overflows": 0,
                }

        source = Silent()
        engine = TriggerEngine(source, window_length=882)
        window = MainWindow(source, engine, fps=60)
        window.resize(width, height)
        window.show()
        self.app.processEvents()
        self.addCleanup(window.close)
        return window

    def test_fits_a_phone(self):
        """430px wide, which is the width the house says to check.

        A row that cannot wrap does not look wrong at this size - it sets the
        window's minimum width and the page stops being resizable at all, so
        this asserts on the width the window actually got.
        """
        window = self.build(430, 820)

        self.assertLessEqual(
            window.minimumSizeHint().width(),
            430,
            "something in the frame refuses to be 430px wide",
        )
        self.assertEqual(window.width(), 430)

    def test_the_readout_reserves_its_height(self):
        """The dock must not grow and shrink under the trace.

        Measured in both states, because the readout says different things in
        each and the reservation is what stops that moving the screen.
        """
        from trigger import TriggerResult
        import numpy as np

        window = self.build(1100, 660)
        heights = set()

        for triggered in (True, False):
            result = TriggerResult(
                channels=[np.zeros(882, dtype=np.float32)],
                triggered=triggered,
                trigger_index=0 if triggered else None,
                pre=0,
                samplerate=44100,
                peak=0.5,
                rms=0.3,
            )
            window._write_readout(result, 0.0)
            self.app.processEvents()
            heights.add(window._readout.height())

        self.assertEqual(
            len(heights), 1, f"the readout changed height between states: {heights}"
        )
        self.assertGreaterEqual(min(heights), 46)


if __name__ == "__main__":
    unittest.main()
