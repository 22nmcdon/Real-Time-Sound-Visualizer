"""The scope screen: a pyqtgraph plot dressed up as a CRT."""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg

SCREEN_BACKGROUND = "#060b06"
TRACE_COLOR = "#3dff7a"
GRID_COLOR = "#2a6b3a"
AXIS_COLOR = "#4f8a5e"
TRIGGER_LINE_COLOR = "#ffb347"
GRID_ALPHA = 0.35


class ScopeRenderer:
    """Owns the plot widget and redraws one triggered window per frame.

    Every frame reuses the same curve object and only swaps its data, which
    is what keeps redraws cheap enough for 60 fps.  Phosphor persistence is a
    later phase; this just clears and draws.
    """

    def __init__(
        self,
        samplerate: float,
        y_range: tuple[float, float] = (-1.0, 1.0),
        trace_color: str = TRACE_COLOR,
    ):
        pg.setConfigOptions(antialias=False)

        self.widget = pg.PlotWidget(background=SCREEN_BACKGROUND)
        plot = self.widget.getPlotItem()
        plot.setMenuEnabled(False)
        plot.hideButtons()
        plot.setMouseEnabled(x=False, y=False)
        plot.showGrid(x=True, y=True, alpha=GRID_ALPHA)
        plot.setYRange(*y_range, padding=0)
        plot.setLabel("left", "amplitude")
        plot.setLabel("bottom", "time", units="ms")
        plot.disableAutoRange()

        axis_pen = pg.mkPen(AXIS_COLOR)
        for side in ("left", "bottom"):
            axis = plot.getAxis(side)
            axis.setPen(axis_pen)
            axis.setTextPen(axis_pen)
            axis.setGrid(0)
        for side in ("top", "right"):
            plot.showAxis(side)
            axis = plot.getAxis(side)
            axis.setPen(axis_pen)
            axis.setStyle(showValues=False)

        self._curve = plot.plot(pen=pg.mkPen(trace_color, width=1.6))
        self._trigger_line = pg.InfiniteLine(
            pos=0.0,
            angle=0,
            pen=pg.mkPen(TRIGGER_LINE_COLOR, width=1, style=pg.QtCore.Qt.PenStyle.DashLine),
        )
        plot.addItem(self._trigger_line, ignoreBounds=True)

        self._plot = plot
        self._samplerate = float(samplerate)
        self._x = np.zeros(0, dtype=np.float64)

    @property
    def samplerate(self) -> float:
        return self._samplerate

    @samplerate.setter
    def samplerate(self, value: float) -> None:
        if float(value) != self._samplerate:
            self._samplerate = float(value)
            self._x = np.zeros(0, dtype=np.float64)  # force a rebuild

    def set_trigger_level(self, level: float) -> None:
        self._trigger_line.setPos(float(level))

    def update_trace(self, samples) -> None:
        """Draw one window.  x is milliseconds from the trigger point."""
        samples = np.asarray(samples)
        if samples.size == 0:
            return
        if samples.size != self._x.size:
            self._rebuild_time_axis(samples.size)
        self._curve.setData(self._x, samples)

    def _rebuild_time_axis(self, n_samples: int) -> None:
        step_ms = 1000.0 / self._samplerate
        self._x = np.arange(n_samples, dtype=np.float64) * step_ms
        self._plot.setXRange(0.0, max(self._x[-1], step_ms), padding=0)
