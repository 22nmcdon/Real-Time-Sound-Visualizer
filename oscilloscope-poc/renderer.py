"""The screen: a plot engraved the way the rest of the house is printed.

The lead sheet is the model. The graticule is the ruling on the paper and the
trace is what is written on it, so the trace is ink - the same charcoal the
chord symbols are lettered in, on the same one-stop-brighter paper.

Two things are allowed to say something in colour. The first is the state of
the trigger: a locked trace is ink; a free-running one is `--unresolved`,
which across the house means open and undecided and is the quietest colour of
the five on purpose.  The readout in the dock says the same thing in words,
and the duplication is deliberate: a player's eye is on the trace, not on the
dock, and by the time you have looked down the signal has moved.  It is the
argument the jazz page makes for putting guide tones on the keys rather than
over the chart.

The second is the right channel, which is the accent.  Two traces need
telling apart and the house has exactly one way to say "this one, not that
one".  It is the accent at rest rather than the accent doing work, because
the right channel is not more important than the left - it is the other one.

Deliberately not rust.  A signal with no edge in it is silence or noise, not
a fault, and nothing on screen calls the person in front of it wrong.
"""

from __future__ import annotations

from collections import deque

import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import QHBoxLayout, QWidget

import branding as house

# Two states, and they are the trace's own. Everything else on the page reads
# the tokens; this reads them too, so a second light would move the trace with
# the rest of the surface.
TRACE_LOCKED = house.CHARCOAL
TRACE_FREE = house.UNRESOLVED
TRACE_RIGHT = house.BLUSH_DEEP

YT = "y-t"
XY = "x-y"
MODES = (YT, XY)

# Past frames drawn behind the live one. Each is a full polyline, so this is
# the one setting on the page that costs frames; eight is what a laptop drew
# at sixty with room to spare.
MAX_PERSISTENCE = 8

# Qt's own "no maximum", which is what a width constraint is lifted back to.
UNCONSTRAINED = 16_777_215


class Stage(QWidget):
    """Holds the plot, and makes it square when the display asks for one.

    X-Y is the one display whose shape carries meaning: a 1:1 figure is a
    circle, and the eye reads how far from round it is as how far from a
    quarter turn the two channels are. On a screen three times wider than it
    is tall, locking the aspect ratio inside the plot keeps the figure honest
    but pushes the x axis out to +/-3 and leaves the shape adrift in the
    middle of it. Constraining the plot itself is the same correction made
    one level out, where there is paper to put the leftover width on.
    """

    def __init__(self, plot):
        super().__init__()
        self._plot = plot
        self._square = False

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        row.addStretch(1)
        # The same out-voting `wrap` does: a box layout divides by stretch and
        # has no notion of "as wide as it may be", so the middle has to win by
        # enough that the two margins round away.
        row.addWidget(plot, house.FILL)
        row.addStretch(1)

    def set_square(self, square: bool) -> None:
        self._square = bool(square)
        self._fit()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit()

    def _fit(self) -> None:
        # Settles in one pass: the height is set by the column above and a
        # change of width cannot alter it, so this never chases itself.
        self._plot.setMaximumWidth(self.height() if self._square else UNCONSTRAINED)


def _fade(colour: str, amount: float) -> pg.QtGui.QColor:
    """A ghost is the trace's own colour, thinned towards the paper.

    Not the trace at lower alpha: overlapping ghosts would then darken where
    they cross, and a ghost that gets *stronger* where the trace repeats is
    the opposite of what persistence is for.
    """
    ink = pg.QtGui.QColor(colour)
    paper = pg.QtGui.QColor(house.PAPER)
    mix = lambda a, b: int(round(b + (a - b) * amount))
    return pg.QtGui.QColor(
        mix(ink.red(), paper.red()),
        mix(ink.green(), paper.green()),
        mix(ink.blue(), paper.blue()),
    )


class ScopeRenderer:
    """Owns the plot and draws one triggered window per frame.

    Every frame reuses its curves and swaps their data, which is what keeps a
    redraw cheap enough for 60 fps. Curves are made once, at the ceiling, and
    hidden rather than destroyed - building a `PlotDataItem` mid-loop is the
    sort of allocation that shows up as a dropped frame rather than as a bug.
    """

    def __init__(self, samplerate: float, y_range: tuple[float, float] = (-1.0, 1.0)):
        # Off, and not as an oversight: an antialiased polyline of a thousand
        # points is the one thing in this app that has to happen sixty times a
        # second, and the trace is a hairline on paper either way.
        pg.setConfigOptions(antialias=False)

        self._view = pg.PlotWidget(background=house.PAPER)
        self.widget = Stage(self._view)
        plot = self._view.getPlotItem()
        plot.setMenuEnabled(False)
        plot.hideButtons()
        plot.setMouseEnabled(x=False, y=False)
        plot.setYRange(*y_range, padding=0)
        plot.disableAutoRange()

        # The ruling. `--line` is every border and rule on the page, and a
        # graticule is exactly that - it is not a second kind of grey.
        plot.showGrid(x=True, y=True, alpha=0.6)

        rule = pg.mkPen(house.LINE, width=house.BORDER)
        self._label_css = {
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

        # Ghosts first, so the live trace is drawn over them however many of
        # them there are. Z-order here is insertion order.
        self._ghosts = [
            plot.plot(pen=pg.mkPen(_fade(TRACE_LOCKED, 0.0), width=1.2))
            for _ in range(MAX_PERSISTENCE)
        ]
        for ghost in self._ghosts:
            ghost.hide()

        self._curves = [
            plot.plot(pen=self._trace_pen(True, 0)),
            plot.plot(pen=self._trace_pen(True, 1)),
        ]
        self._curves[1].hide()

        # The trigger level, where the accent is doing work. Dashed, because
        # it is a line you set rather than a line the signal drew.
        dash = pg.QtCore.Qt.PenStyle.DashLine
        self._trigger_line = pg.InfiniteLine(
            pos=0.0,
            angle=0,
            pen=pg.mkPen(house.BLUSH_DEEP, width=house.BORDER, style=dash),
        )
        plot.addItem(self._trigger_line, ignoreBounds=True)

        # Where in the window the edge sits. Off screen until the window has
        # a run-up to show, which at position 0 it has not.
        self._position_line = pg.InfiniteLine(
            pos=0.0,
            angle=90,
            pen=pg.mkPen(house.BLUSH, width=house.BORDER, style=dash),
        )
        plot.addItem(self._position_line, ignoreBounds=True)
        self._position_line.hide()

        self._plot = plot
        self._samplerate = float(samplerate)
        self._y_range = tuple(y_range)
        self._x = np.zeros(0, dtype=np.float64)
        self._locked = True
        self._mode = YT
        self._persistence = 0
        self._history: deque = deque(maxlen=MAX_PERSISTENCE)
        self._apply_mode()

    # ------------------------------------------------------------------ pens

    def _trace_pen(self, locked: bool, channel: int = 0):
        if not locked:
            return pg.mkPen(TRACE_FREE, width=1.6)
        return pg.mkPen(TRACE_LOCKED if channel == 0 else TRACE_RIGHT, width=1.6)

    # ---------------------------------------------------------------- knobs

    @property
    def samplerate(self) -> float:
        return self._samplerate

    @samplerate.setter
    def samplerate(self, value: float) -> None:
        if float(value) != self._samplerate:
            self._samplerate = float(value)
            self._x = np.zeros(0, dtype=np.float64)  # force a rebuild

    @property
    def mode(self) -> str:
        return self._mode

    @mode.setter
    def mode(self, value: str) -> None:
        value = str(value).lower()
        if value not in MODES:
            raise ValueError(f"mode must be one of {MODES}, got {value!r}")
        if value == self._mode:
            return
        self._mode = value
        self._history.clear()
        self._x = np.zeros(0, dtype=np.float64)
        self._apply_mode()

    @property
    def persistence(self) -> int:
        """How many past frames stay on the paper behind the live one."""
        return self._persistence

    @persistence.setter
    def persistence(self, value: int) -> None:
        self._persistence = int(np.clip(int(value), 0, MAX_PERSISTENCE))
        if self._persistence == 0:
            self._history.clear()
        for index, ghost in enumerate(self._ghosts):
            if index >= self._persistence:
                ghost.hide()

    def set_trigger_level(self, level: float) -> None:
        self._trigger_line.setPos(float(level))

    # --------------------------------------------------------------- drawing

    def _apply_mode(self) -> None:
        """Two displays, one plot. What changes is what the axes mean."""
        xy = self._mode == XY

        self._plot.setLabel("left", house.caps("amplitude"), **self._label_css)
        if xy:
            # Equal units on both axes, or a circle is an ellipse and every
            # phase reading off this display is wrong.
            self._plot.setAspectLocked(True, ratio=1.0)
            self._plot.setLabel("bottom", house.caps("left"), **self._label_css)
            self._plot.setLabel("left", house.caps("right"), **self._label_css)
            self._plot.setXRange(*self._y_range, padding=0)
            self._plot.setYRange(*self._y_range, padding=0)
            self._trigger_line.hide()
            self._position_line.hide()
            self.widget.set_square(True)
        else:
            self._plot.setAspectLocked(False)
            self._plot.setLabel("bottom", house.caps("time"), units="ms", **self._label_css)
            self._plot.setYRange(*self._y_range, padding=0)
            self._trigger_line.show()
            self.widget.set_square(False)

        for ghost in self._ghosts:
            ghost.hide()

    def update(self, result) -> None:
        """Draw one captured frame, whichever way the display is set."""
        channels = [np.asarray(channel) for channel in getattr(result, "channels", [])]
        if not channels or channels[0].size == 0:
            return

        if self._mode == XY:
            self._draw_xy(channels)
        else:
            self._draw_yt(channels, bool(result.triggered), int(getattr(result, "pre", 0)))

    def update_trace(self, samples, triggered: bool = True) -> None:
        """One channel, for callers that only have the one. Kept because the
        renderer predates stereo and a plot that can draw a bare array is
        worth keeping testable."""
        self._draw_yt([np.asarray(samples)], triggered, 0)

    def _draw_yt(self, channels, triggered: bool, pre: int) -> None:
        length = channels[0].size
        if length != self._x.size:
            self._rebuild_time_axis(length)

        # Only when it changes: building a pen is cheap and doing it sixty
        # times a second for a value that moves once a minute is not the sort
        # of thing this loop should be spending on.
        if triggered != self._locked:
            self._locked = triggered
            for index, curve in enumerate(self._curves):
                curve.setPen(self._trace_pen(triggered, index))

        self._draw_ghosts(self._x, channels[0])

        self._curves[0].setData(self._x, channels[0])
        self._curves[0].show()

        if len(channels) > 1 and channels[1].size == length:
            self._curves[1].setData(self._x, channels[1])
            self._curves[1].show()
        else:
            self._curves[1].hide()

        if pre > 0 and pre < length:
            self._position_line.setPos(float(self._x[pre]))
            self._position_line.show()
        else:
            self._position_line.hide()

    def _draw_xy(self, channels) -> None:
        """Left against right: the figure two channels make together.

        One channel has no figure to make - a signal against itself is the
        diagonal, always, whatever it is doing - so a mono source draws
        nothing here rather than drawing a line that means nothing.
        """
        self._curves[1].hide()
        if len(channels) < 2 or channels[1].size != channels[0].size:
            self._curves[0].hide()
            for ghost in self._ghosts:
                ghost.hide()
            return

        if not self._locked:
            self._locked = True
            self._curves[0].setPen(self._trace_pen(True, 0))

        self._draw_ghosts(channels[0], channels[1])
        self._curves[0].setData(channels[0], channels[1])
        self._curves[0].show()

    def _draw_ghosts(self, x, y) -> None:
        """The frames before this one, fading back towards the paper."""
        if self._persistence == 0:
            return

        depth = self._persistence
        for age, (past_x, past_y) in enumerate(reversed(self._history)):
            if age >= depth:
                break
            ghost = self._ghosts[age]
            # Newest ghost nearly ink, oldest nearly paper.
            ghost.setPen(pg.mkPen(_fade(TRACE_LOCKED, 1.0 - (age + 1) / (depth + 1)), width=1.2))
            ghost.setData(past_x, past_y)
            ghost.show()
        for age in range(min(len(self._history), depth), depth):
            self._ghosts[age].hide()

        # Copies, because the next capture reuses nothing but the ring buffer
        # underneath these views may well be written over.
        self._history.append((np.array(x, copy=True), np.array(y, copy=True)))

    def _rebuild_time_axis(self, n_samples: int) -> None:
        step_ms = 1000.0 / self._samplerate
        self._x = np.arange(n_samples, dtype=np.float64) * step_ms
        self._plot.setXRange(0.0, max(self._x[-1], step_ms), padding=0)
        self._history.clear()
