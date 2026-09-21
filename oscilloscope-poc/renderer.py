"""The screen: a plot engraved the way the rest of the house is printed.

The lead sheet is the model. The graticule is the ruling on the paper and the
trace is what is written on it, so the trace is ink - the same charcoal the
chord symbols are lettered in, on the same one-stop-brighter paper.

One thing is allowed to say something in colour, and it is the state of the
trigger.  A locked trace is ink; a free-running one is `--unresolved`, which
across the house means open and undecided and is the quietest colour of the
five on purpose.  The readout in the dock says the same thing in words, and
the duplication is deliberate: a player's eye is on the trace, not on the
dock, and by the time you have looked down the signal has moved.  It is the
argument the jazz page makes for putting guide tones on the keys rather than
over the chart.

Deliberately not rust.  A signal with no edge in it is silence or noise, not
a fault, and nothing on screen calls the person in front of it wrong.
"""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg

import branding as house

# Two states, and they are the trace's own. Everything else on the page reads
# the tokens; this reads them too, so a second light would move the trace with
# the rest of the surface.
TRACE_LOCKED = house.CHARCOAL
TRACE_FREE = house.UNRESOLVED


class ScopeRenderer:
    """Owns the plot and draws one triggered window per frame.

    Every frame reuses the one curve and swaps its data, which is what keeps a
    redraw cheap enough for 60 fps.  Persistence is a later phase; this clears
    and draws.
    """

    def __init__(self, samplerate: float, y_range: tuple[float, float] = (-1.0, 1.0)):
        # Off, and not as an oversight: an antialiased polyline of a thousand
        # points is the one thing in this app that has to happen sixty times a
        # second, and the trace is a hairline on paper either way.
        pg.setConfigOptions(antialias=False)

        self.widget = pg.PlotWidget(background=house.PAPER)
        plot = self.widget.getPlotItem()
        plot.setMenuEnabled(False)
        plot.hideButtons()
        plot.setMouseEnabled(x=False, y=False)
        plot.setYRange(*y_range, padding=0)
        plot.disableAutoRange()

        # The ruling. `--line` is every border and rule on the page, and a
        # graticule is exactly that - it is not a second kind of grey.
        plot.showGrid(x=True, y=True, alpha=0.6)

        rule = pg.mkPen(house.LINE, width=house.BORDER)
        label_css = {
            "color": house.TEXT_SOFT,
            "font-size": f"{house.EYEBROW_SIZE}px",
            "letter-spacing": f"{house.EYEBROW_TRACKING}em",
        }

        for side in ("left", "bottom"):
            axis = plot.getAxis(side)
            axis.setPen(rule)
            axis.setTextPen(pg.mkPen(house.TEXT_SOFT))
            axis.setTickFont(house.font(house.SANS, 10, 400))

        # A sheet has an edge on all four sides, and the two without numbers
        # are drawn by `Sheet` as the paper's own 1px border. They were two
        # more axes here first, which is both the wrong thing to call them and
        # expensive: pyqtgraph hangs the grid off the axes, so showing four
        # draws every grid line twice and took 54 fps to 32. Measured, not
        # guessed - see the note on `Sheet`.

        plot.setLabel("left", house.caps("amplitude"), **label_css)
        plot.setLabel("bottom", house.caps("time"), units="ms", **label_css)

        self._curve = plot.plot(pen=self._trace_pen(True))

        # The trigger level, where the accent is doing work. Dashed, because
        # it is a line you set rather than a line the signal drew.
        self._trigger_line = pg.InfiniteLine(
            pos=0.0,
            angle=0,
            pen=pg.mkPen(house.BLUSH_DEEP, width=house.BORDER, style=pg.QtCore.Qt.PenStyle.DashLine),
        )
        plot.addItem(self._trigger_line, ignoreBounds=True)

        self._plot = plot
        self._samplerate = float(samplerate)
        self._x = np.zeros(0, dtype=np.float64)
        self._locked = True

    def _trace_pen(self, locked: bool):
        return pg.mkPen(TRACE_LOCKED if locked else TRACE_FREE, width=1.6)

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

    def update_trace(self, samples, triggered: bool = True) -> None:
        """Draw one window. x is milliseconds from the trigger point."""
        samples = np.asarray(samples)
        if samples.size == 0:
            return

        if samples.size != self._x.size:
            self._rebuild_time_axis(samples.size)

        # Only when it changes: building a pen is cheap and doing it sixty
        # times a second for a value that moves once a minute is not the sort
        # of thing this loop should be spending on.
        if triggered != self._locked:
            self._locked = triggered
            self._curve.setPen(self._trace_pen(triggered))

        self._curve.setData(self._x, samples)

    def _rebuild_time_axis(self, n_samples: int) -> None:
        step_ms = 1000.0 / self._samplerate
        self._x = np.arange(n_samples, dtype=np.float64) * step_ms
        self._plot.setXRange(0.0, max(self._x[-1], step_ms), padding=0)
