"""Window shell: the scope screen plus the few controls the POC needs."""

from __future__ import annotations

import time

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from renderer import ScopeRenderer
from trigger import EDGES, MIN_WINDOW

LEVEL_SLIDER_SCALE = 1000  # slider ticks per unit of amplitude
MIN_WINDOW_MS = 2
MAX_WINDOW_MS = 200  # well inside the engine's own 1 s ceiling
STATUS_INTERVAL = 0.2  # seconds; slower than the frame rate so text stays readable

STYLE_SHEET = """
QMainWindow, QWidget { background-color: #101410; color: #bfe6c8; }
QLabel { color: #bfe6c8; }
QLabel#status { color: #9fd6ae; font-family: monospace; }
QComboBox {
    background-color: #1b241b; color: #d8f5e0;
    border: 1px solid #3d6b47; border-radius: 3px; padding: 2px 6px;
}
QComboBox QAbstractItemView {
    background-color: #1b241b; color: #d8f5e0; selection-background-color: #2f5c3a;
}
QSlider::groove:horizontal { height: 4px; background: #2a3a2d; border-radius: 2px; }
QSlider::handle:horizontal {
    background: #3dff7a; width: 12px; margin: -5px 0; border-radius: 6px;
}
"""


class MainWindow(QMainWindow):
    """Wires source -> trigger -> renderer to a QTimer, and exposes the knobs."""

    def __init__(self, source, engine, fps: int = 60, parent=None):
        super().__init__(parent)
        self._source = source
        self._engine = engine

        self.setWindowTitle("Oscilloscope POC")
        self.setStyleSheet(STYLE_SHEET)
        self.resize(1000, 620)

        self._renderer = ScopeRenderer(samplerate=engine.samplerate)
        self._renderer.set_trigger_level(engine.trigger_level)

        self._level_slider = QSlider(Qt.Orientation.Horizontal)
        self._level_slider.setRange(-LEVEL_SLIDER_SCALE, LEVEL_SLIDER_SCALE)
        self._level_slider.setValue(round(engine.trigger_level * LEVEL_SLIDER_SCALE))
        self._level_slider.valueChanged.connect(self._on_level_changed)
        self._level_value = QLabel()

        self._edge_box = QComboBox()
        self._edge_box.addItems([edge.capitalize() for edge in EDGES])
        self._edge_box.setCurrentIndex(EDGES.index(engine.trigger_edge))
        self._edge_box.currentIndexChanged.connect(self._on_edge_changed)

        self._window_slider = QSlider(Qt.Orientation.Horizontal)
        self._window_slider.setRange(MIN_WINDOW_MS, MAX_WINDOW_MS)
        self._window_slider.setValue(self._clamp_window_ms(self._current_window_ms()))
        self._window_slider.valueChanged.connect(self._on_window_changed)
        self._window_value = QLabel()

        self._status = QLabel()
        self._status.setObjectName("status")

        self.setCentralWidget(self._build_layout())
        self._sync_labels()

        # Frame timing, for the fps readout and the throttled status line.
        self._frame_count = 0
        self._last_status_time = time.perf_counter()
        self._fps = 0.0
        self._last_result = None

        interval_ms = max(1, round(1000 / max(1, int(fps))))
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.timeout.connect(self._on_frame)
        self._timer.start(interval_ms)

    # ---------------------------------------------------------------- layout

    def _build_layout(self) -> QWidget:
        controls = QHBoxLayout()
        controls.setSpacing(10)
        controls.addWidget(QLabel("Trigger level"))
        controls.addWidget(self._level_slider, 2)
        controls.addWidget(self._level_value)
        controls.addSpacing(16)
        controls.addWidget(QLabel("Edge"))
        controls.addWidget(self._edge_box)
        controls.addSpacing(16)
        controls.addWidget(QLabel("Window"))
        controls.addWidget(self._window_slider, 2)
        controls.addWidget(self._window_value)

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        layout.addWidget(self._renderer.widget, 1)
        layout.addLayout(controls)
        layout.addWidget(self._status)

        central = QWidget()
        central.setLayout(layout)
        return central

    # --------------------------------------------------------------- helpers

    def _current_window_ms(self) -> int:
        return round(1000 * self._engine.window_length / self._engine.samplerate)

    def _clamp_window_ms(self, value: int) -> int:
        return max(MIN_WINDOW_MS, min(MAX_WINDOW_MS, int(value)))

    def _sync_labels(self) -> None:
        self._level_value.setText(f"{self._engine.trigger_level:+.3f}")
        self._window_value.setText(
            f"{self._current_window_ms():3d} ms / {self._engine.window_length} samples"
        )

    # ---------------------------------------------------------------- slots

    def _on_level_changed(self, value: int) -> None:
        level = value / LEVEL_SLIDER_SCALE
        self._engine.trigger_level = level
        self._renderer.set_trigger_level(level)
        self._sync_labels()

    def _on_edge_changed(self, index: int) -> None:
        self._engine.trigger_edge = EDGES[index]

    def _on_window_changed(self, value_ms: int) -> None:
        samples = round(value_ms * self._engine.samplerate / 1000)
        self._engine.window_length = max(MIN_WINDOW, samples)
        self._sync_labels()

    def _on_frame(self) -> None:
        result = self._engine.capture()
        self._renderer.update_trace(result.samples)
        self._last_result = result
        self._frame_count += 1

        now = time.perf_counter()
        elapsed = now - self._last_status_time
        if elapsed >= STATUS_INTERVAL:
            self._fps = self._frame_count / elapsed
            self._frame_count = 0
            self._last_status_time = now
            self._update_status(result)

    def _update_status(self, result) -> None:
        status = self._source.status()
        rate = status.get("samplerate", self._engine.samplerate)
        channels = status.get("channels", self._source.channels)
        state = "LOCKED" if result.triggered else "FREE RUN"
        parts = [
            f"{rate:.0f} Hz",
            f"{channels} ch",
            f"trigger {state}",
            f"peak {result.peak:.3f}",
            f"rms {result.rms:.3f}",
            f"{self._fps:.0f} fps",
        ]
        if not status.get("running", True):
            parts.insert(0, "INPUT STOPPED")
        overflows = status.get("overflows", 0)
        if overflows:
            parts.append(f"overflows {overflows}")
        device = status.get("device")
        if device:
            parts.append(str(device))
        self._status.setText("  |  ".join(parts))

    # --------------------------------------------------------------- Qt hooks

    def closeEvent(self, event) -> None:
        self._timer.stop()
        try:
            self._source.stop()
        finally:
            super().closeEvent(event)
