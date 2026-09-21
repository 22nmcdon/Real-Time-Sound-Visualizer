"""The frame: a head, the screen, and a dock. Nothing scrolls but the middle.

Three zones, as the house lays a page out. The head is furniture at its own
height, the dock is furniture at its own height, and the screen takes every
pixel the other two do not - so anything added to the head or the dock is
taken out of the trace and has to earn it.

The strip under the head is the transport. What is on it is what you reach
for while the signal is running, in three rows, ordered by how often a hand
lands on them: what the scope is doing, where the trigger is, and how much
time is on screen. Each row is groups, and each group is one row of its own
below the breakpoint - which is what keeps the top of the screen from moving
when the window narrows.

Every knob added here was earned by the engine already having it. Pre-trigger,
holdoff, a trigger source and a second channel were all in `trigger.py` with
no way to reach them from the page, which is the same as not having them.
"""

from __future__ import annotations

import time

import numpy as np
from PyQt6.QtCore import QEvent, QSize, Qt, QTimer
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

import branding as house
import measure
import renderer as render
from renderer import ScopeRenderer
from trigger import EDGES, MIN_WINDOW

LEVEL_SLIDER_SCALE = 1000   # slider ticks per unit of amplitude
MIN_WINDOW_MS = 2
MAX_WINDOW_MS = 200         # well inside the engine's own 1 s ceiling
MAX_HOLDOFF_MS = 50

# Auto draws whatever came back; normal holds the last locked frame rather
# than showing an untriggered one; single keeps the first and stops.
AUTO, NORMAL, SINGLE = "auto", "normal", "single"
TRIGGER_MODES = (AUTO, NORMAL, SINGLE)

# Slower than the frame rate, because the readout is read rather than watched:
# words changing sixty times a second are words nobody finishes.
READOUT_INTERVAL = 0.2

# A sample at full scale is a sample the converter may have clipped.
CLIP_LEVEL = 0.999

# Below this the input is silence, and silence has no edges in it. Used only
# to tell "nothing is playing" apart from "something is playing and the
# trigger is not catching it", which are the same picture and different
# problems.
SILENCE = 0.01

# The harmonic reading gets its own block, long enough for bins fine enough to
# tell a harmonic from the window's skirt. Tied to the displayed window it
# would follow the timebase, and a scope's timebase is set to see the
# waveform, not to resolve a spectrum - at 9 ms it read a pure sine as 36%
# distorted. See `measure.MIN_FFT_SIZE`.
HARMONIC_BLOCK = 4096

# Below the breakpoint every control takes a line of its own, and eleven
# lines of transport would leave the trace a strip. The strip is capped at
# this share of the window instead and scrolls past it: the controls stay
# legible, the screen stays a screen, and nothing is hidden behind a
# disclosure the person has to find.
NARROW_TRANSPORT_SHARE = 0.42

# What autoset aims for: enough cycles to see the shape, few enough to see the
# detail. Four is what a bench scope's own autoset lands on.
AUTOSET_CYCLES = 4

# Nothing on this surface animates, and that is the house rule followed rather
# than skipped. The one thing the jazz page breathes is a verdict that arrives
# two notes after the moment it is about, so it has to be catchable out of the
# corner of an eye. Nothing here is like that: the trace redraws sixty times a
# second and every state this page has - locked, free running, clipping - is
# already written on it. A breathing chip beside a live trace would be motion
# competing with the one thing on the page worth watching.


class StatusChip(QLabel):
    """A state you are in, so it is a pill and it whispers."""

    def __init__(self, text: str, state: str = "loading"):
        super().__init__(house.caps(text))
        self.setProperty("weight", "chip")
        self.setFont(house.control_font())
        self.say(text, state)

    def say(self, text: str, state: str) -> None:
        self.setText(house.caps(text))
        self.setProperty("state", state)
        house.restyle(self)


class Switch(QWidget):
    """Two sides of one thing, with a side chosen.

    A dropdown would be the wrong shape for this: rising and falling are not
    a list you pick from, they are one setting with two positions, and the
    house says that is a switch.
    """

    def __init__(self, options, chosen=0, on_change=None):
        super().__init__()
        self._on_change = on_change
        self._buttons = []

        frame = QFrame()
        frame.setObjectName("switchFrame")
        row = QHBoxLayout(frame)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)

        for index, label in enumerate(options):
            button = QPushButton(house.caps(label))
            button.setProperty("weight", "switch")
            button.setFont(house.control_font())
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _=False, i=index: self.choose(i))
            row.addWidget(button)
            self._buttons.append(button)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(frame)

        self._chosen = -1
        self.choose(chosen, announce=False)

    @property
    def chosen(self) -> int:
        return self._chosen

    def choose(self, index: int, announce: bool = True) -> None:
        if index == self._chosen:
            return

        self._chosen = index
        for at, button in enumerate(self._buttons):
            button.setProperty("chosen", "true" if at == index else "false")
            house.restyle(button)

        if announce and self._on_change is not None:
            self._on_change(index)


class Strip(QScrollArea):
    """A scroll area exactly as tall as what is in it, up to its maximum.

    Qt's own answer is a fixed default height and a scrollbar beside three
    rows that fit, so the height has to come from the contents. Computing it
    once and calling `setFixedHeight` is the version of this that was wrong
    first: the first layout pass reported 129px for a strip that settled at
    144, the strip was pinned to the early number and the bottom row was cut
    off. Answering with a `sizeHint` instead means Qt re-asks whenever the
    contents change, which is the question it was always trying to answer.
    """

    def __init__(self, inner):
        super().__init__()
        self._wanted = -1
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.setWidget(inner)
        inner.installEventFilter(self)

    def sizeHint(self) -> QSize:
        inner = self.widget()
        if inner is None:
            return super().sizeHint()
        # Unclamped on purpose: a layout bounds a size hint by the widget's
        # own maximum, which is where the cap is set.
        return QSize(super().sizeHint().width(), inner.sizeHint().height())

    def eventFilter(self, watched, event):
        """Tell the layout above when the answer has changed.

        A parent layout caches what its children asked for and re-reads it
        only when told to. The strip's first honest measurement comes after
        the fonts are resolved, by which time the column above has already
        banked the earlier one - which is how three rows of controls ended up
        in the space two of them asked for.
        """
        if watched is self.widget() and event.type() == QEvent.Type.LayoutRequest:
            wanted = watched.sizeHint().height()
            # Only on a change, or `updateGeometry` inside a layout pass asks
            # for the pass that is already running.
            if wanted != self._wanted:
                self._wanted = wanted
                self.updateGeometry()
        return False


class Field(QWidget):
    """A label over a control, which is what the eyebrow is for."""

    def __init__(self, name: str, control: QWidget, value: QLabel | None = None):
        super().__init__()
        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(3)
        column.addWidget(house.eyebrow(name))

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)
        row.addWidget(control, 1)
        if value is not None:
            row.addWidget(value)
        column.addLayout(row)


class MainWindow(QMainWindow):
    """Wires source -> trigger -> screen to a timer, and holds the knobs."""

    def __init__(self, source, engine, fps: int = 60, parent=None):
        super().__init__(parent)
        self._source = source
        self._engine = engine
        self._channels = max(1, int(getattr(source, "channels", 1)))

        self.setWindowTitle("Oscilloscope")
        self.setStyleSheet(house.style_sheet())
        self.resize(1100, 700)

        self._renderer = ScopeRenderer(samplerate=engine.samplerate)
        self._renderer.set_trigger_level(engine.trigger_level)

        self._running = True
        self._trigger_mode = AUTO
        self._caught = False        # single mode: the frame is on the paper

        self._build_head()
        self._build_transport()
        self._build_dock()
        self.setCentralWidget(self._build_frame())

        self._sync_labels()

        self._frames = 0
        self._last_readout = time.perf_counter()
        self._fps = 0.0

        # Before the window is ever shown: see `_narrow`.
        self._apply_breakpoint(self.width())

        interval = max(1, round(1000 / max(1, int(fps))))
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.timeout.connect(self._on_frame)
        self._timer.start(interval)

    # ------------------------------------------------------------------ head

    def _build_head(self) -> None:
        """Feel, title, credit - engraved along a line rather than centred.

        A lead sheet says these three things at the top and this is the same
        three: where the signal is from, what you are looking at, and on what.
        They live up here rather than over the screen so they do not scroll
        away with the thing they name.
        """
        status = self._source.status()

        self._style_mark = QLabel(house.caps("live input"))
        self._style_mark.setFont(house.control_font())
        self._style_mark.setStyleSheet(f"color: {house.TEXT_SOFT};")

        title = QLabel(house.caps("Oscilloscope"))
        title.setFont(house.heading_font(19))
        title.setStyleSheet(f"color: {house.CHARCOAL};")

        self._credit = house.Elide(str(status.get("device", "")) or "no input")
        self._credit.setFont(house.credit_font())
        self._credit.setStyleSheet(f"color: {house.TEXT_SOFT};")

        self._chip = StatusChip("starting", "loading")

        self._head = house.Reflow(
            lead=[self._style_mark, title],
            trail=[self._credit, self._chip],
        )

    # ------------------------------------------------------------- transport

    def _build_transport(self) -> None:
        self._groups = []

        run_group = self._group([
            (Field("", self._build_run_button()), 0),
            (Field("mode", self._build_mode_switch()), 0),
            (Field("", self._build_autoset_button()), 0),
        ])

        display_group = self._group([
            (Field("display", self._build_display_switch()), 0),
            (Field("persistence", *self._build_persistence()), 1),
        ])

        self._build_trigger()
        trigger_fields = [
            (Field("trigger level", self._level_slider, self._level_value), 1),
            (Field("edge", self._edge_switch), 0),
        ]
        # A source switch on a mono input would be a control with one honest
        # position, which is furniture pretending to be a knob.
        if self._channels > 1:
            trigger_fields.append((Field("source", self._build_source_switch()), 0))
        trigger_group = self._group(trigger_fields)

        timing_group = self._group([
            (Field("window", *self._build_window()), 1),
            (Field("position", *self._build_position()), 1),
            (Field("holdoff", *self._build_holdoff()), 1),
        ])

        # Every group carries a stretch, because a group's size policy is
        # `Ignored` - it must not put a floor under the window - and a layout
        # hands an ignored widget exactly its stretch share of the row. At
        # zero that is no width at all, and the run button and autoset simply
        # were not on the page.
        self._rows = [
            self._row([(run_group, 3), (display_group, 4)]),
            self._row([(trigger_group, 1)]),
            self._row([(timing_group, 1)]),
        ]

        self._transport = QWidget()
        column = QVBoxLayout(self._transport)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(12)
        for row, _ in self._rows:
            column.addWidget(row)

        self._strip = Strip(self._transport)

        # None rather than False, so the first call always applies a state -
        # a window opened narrow must reflow before it is shown, or its own
        # minimum width holds it wide and no resize can get it back.
        self._narrow = None

    def _group(self, fields) -> QWidget:
        """One cluster of controls, which is one line of its own when narrow."""
        holder = QWidget()
        row = QHBoxLayout(holder)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(22)
        for widget, stretch in fields:
            row.addWidget(widget, stretch)
        if not any(stretch for _, stretch in fields):
            # A row of controls that all decline to stretch leaves the layout
            # to hand the slack out by size policy, which spreads them across
            # the group instead of keeping them together. One trailing spring
            # says where the slack goes.
            row.addStretch(1)

        # Same reason as `Reflow`: the transport rearranges to fit, so it
        # must not be what stops the window fitting.
        holder.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        holder.setMinimumWidth(0)
        self._groups.append(row)
        return holder

    def _row(self, groups):
        holder = QWidget()
        layout = QHBoxLayout(holder)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(28)
        for group, stretch in groups:
            layout.addWidget(group, stretch)
        return holder, layout

    # -- the controls themselves ------------------------------------------

    def _build_run_button(self) -> QPushButton:
        self._run_button = QPushButton()
        self._run_button.setProperty("weight", "filled")
        self._run_button.setFont(house.control_font())
        self._run_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._run_button.clicked.connect(self._on_run_clicked)
        return self._run_button

    def _build_autoset_button(self) -> QPushButton:
        button = QPushButton(house.caps("autoset"))
        button.setProperty("weight", "pill")
        button.setFont(house.control_font())
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(self._on_autoset)
        return button

    def _build_mode_switch(self) -> Switch:
        self._mode_switch = Switch(
            list(TRIGGER_MODES),
            chosen=TRIGGER_MODES.index(self._trigger_mode),
            on_change=self._on_mode_changed,
        )
        return self._mode_switch

    def _build_display_switch(self) -> Switch:
        self._display_switch = Switch(
            ["y-t", "x-y"], chosen=0, on_change=self._on_display_changed
        )
        return self._display_switch

    def _build_source_switch(self) -> Switch:
        self._source_switch = Switch(
            ["left", "right"],
            chosen=min(self._engine.trigger_source, 1),
            on_change=self._on_source_changed,
        )
        return self._source_switch

    def _build_trigger(self) -> None:
        self._level_slider = QSlider(Qt.Orientation.Horizontal)
        self._level_slider.setRange(-LEVEL_SLIDER_SCALE, LEVEL_SLIDER_SCALE)
        self._level_slider.setValue(round(self._engine.trigger_level * LEVEL_SLIDER_SCALE))
        self._level_slider.valueChanged.connect(self._on_level_changed)
        self._level_value = self._reading_label()

        self._edge_switch = Switch(
            list(EDGES),
            chosen=EDGES.index(self._engine.trigger_edge),
            on_change=self._on_edge_changed,
        )

    def _build_window(self):
        self._window_slider = QSlider(Qt.Orientation.Horizontal)
        self._window_slider.setRange(MIN_WINDOW_MS, MAX_WINDOW_MS)
        self._window_slider.setValue(self._clamp_window_ms(self._current_window_ms()))
        self._window_slider.valueChanged.connect(self._on_window_changed)
        self._window_value = self._reading_label()
        return self._window_slider, self._window_value

    def _build_position(self):
        self._position_slider = QSlider(Qt.Orientation.Horizontal)
        self._position_slider.setRange(0, 90)
        self._position_slider.setValue(round(self._engine.position * 100))
        self._position_slider.valueChanged.connect(self._on_position_changed)
        self._position_value = self._reading_label()
        return self._position_slider, self._position_value

    def _build_holdoff(self):
        self._holdoff_slider = QSlider(Qt.Orientation.Horizontal)
        self._holdoff_slider.setRange(0, MAX_HOLDOFF_MS)
        self._holdoff_slider.setValue(round(self._engine.holdoff_ms))
        self._holdoff_slider.valueChanged.connect(self._on_holdoff_changed)
        self._holdoff_value = self._reading_label()
        return self._holdoff_slider, self._holdoff_value

    def _build_persistence(self):
        self._persistence_slider = QSlider(Qt.Orientation.Horizontal)
        self._persistence_slider.setRange(0, render.MAX_PERSISTENCE)
        self._persistence_slider.setValue(0)
        self._persistence_slider.valueChanged.connect(self._on_persistence_changed)
        self._persistence_value = self._reading_label()
        return self._persistence_slider, self._persistence_value

    def _reading_label(self) -> QLabel:
        label = QLabel()
        label.setFont(house.body_font(13, 400))
        label.setStyleSheet(f"color: {house.TEXT_SOFT};")
        return label

    # ------------------------------------------------------------------ dock

    def _build_dock(self) -> None:
        """What the screen just said, in words.

        It reserves its height whether or not there is anything in it. A dock
        that grew and shrank under the trace would move the one thing on the
        page you are trying to watch.
        """
        self._verdict = QLabel()
        self._verdict.setFont(house.heading_font(17))

        self._detail = QLabel()
        self._detail.setFont(house.body_font(13, 400))
        self._detail.setStyleSheet(f"color: {house.TEXT_SOFT};")

        looking = house.eyebrow("looking for")
        self._looking = QLabel()
        self._looking.setFont(house.heading_font(15))
        self._looking.setStyleSheet(f"color: {house.CHARCOAL};")

        right = QWidget()
        right_row = QHBoxLayout(right)
        right_row.setContentsMargins(0, 0, 0, 0)
        right_row.setSpacing(8)
        right_row.addWidget(looking)
        right_row.addWidget(self._looking)

        self._readout = house.Reflow(
            lead=[self._verdict, self._detail], trail=[right], spacing=18
        )
        self._readout.setMinimumHeight(house.RESERVED_ROW)

        # What the frame measures, which is a different kind of statement from
        # what the scope is doing and so is a line of its own. The note is
        # here and not on the trace for the same reason the verdict is: it is
        # read, and reading happens at the bottom of the page.
        self._pitch = QLabel()
        self._pitch.setFont(house.heading_font(15))
        self._pitch.setStyleSheet(f"color: {house.CHARCOAL};")

        self._numbers = QLabel()
        self._numbers.setFont(house.mono_font(12))
        self._numbers.setStyleSheet(f"color: {house.TEXT_SOFT};")

        self._measurements = house.Reflow(
            lead=[house.eyebrow("measured"), self._pitch],
            trail=[self._numbers],
            spacing=12,
        )

        self._foot = house.Reflow(
            lead=[
                self._legend(house.CHARCOAL, "left"),
                self._legend(house.BLUSH_DEEP, "right"),
                self._legend(house.UNRESOLVED, "free run"),
            ],
            trail=[self._colophon()],
            spacing=18,
        )

    def _legend(self, colour: str, text: str) -> QWidget:
        """A dot and a word. Needed because the trace says something in
        colour, and a colour that means something has to be named once."""
        size = 8
        dot = QLabel()
        dot.setFixedSize(size, size)
        dot.setStyleSheet(
            f"background: {colour}; border-radius: {house.dot_radius(size)}px;"
        )

        label = QLabel(text)
        label.setFont(house.body_font(12, 400))
        label.setStyleSheet(f"color: {house.TEXT_SOFT};")

        holder = QWidget()
        row = QHBoxLayout(holder)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(7)
        row.addWidget(dot)
        row.addWidget(label)
        return holder

    def _colophon(self) -> QLabel:
        """The house signature: quiet, factual, and about the machine."""
        status = self._source.status()
        parts = [
            "trigger.py",
            f"{status.get('samplerate', self._engine.samplerate):.0f} Hz",
            f"{status.get('channels', self._channels)} ch",
        ]
        blocksize = status.get("blocksize")
        if blocksize:
            parts.append(f"{blocksize}-sample blocks")

        label = QLabel(" · ".join(parts))
        label.setFont(house.mono_font(12))
        label.setStyleSheet(f"color: {house.TEXT_SOFT};")
        return label

    # ----------------------------------------------------------------- frame

    def _build_frame(self) -> QWidget:
        top = QWidget()
        top.setObjectName("topBar")
        top.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        head_column = QWidget()
        stacked = QVBoxLayout(head_column)
        stacked.setContentsMargins(0, 0, 0, 0)
        stacked.setSpacing(12)
        stacked.addWidget(self._head)
        stacked.addWidget(self._strip)

        top_column = QVBoxLayout(top)
        top_column.setContentsMargins(0, 10, 0, 12)
        top_column.addWidget(house.wrap(head_column))

        screen = QWidget()
        screen_column = QVBoxLayout(screen)
        screen_column.setContentsMargins(0, 18, 0, 14)
        screen_column.addWidget(house.wrap(house.Sheet(self._renderer.widget)))

        dock_inner = QWidget()
        dock_stack = QVBoxLayout(dock_inner)
        dock_stack.setContentsMargins(0, 0, 0, 0)
        dock_stack.setSpacing(10)
        dock_stack.addWidget(self._readout)
        dock_stack.addWidget(self._measurements)
        dock_stack.addWidget(self._foot)

        dock = QWidget()
        dock.setObjectName("dock")
        dock.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        dock_column = QVBoxLayout(dock)
        dock_column.setContentsMargins(0, 12, 0, 14)
        dock_column.addWidget(house.wrap(dock_inner))

        central = QWidget()
        column = QVBoxLayout(central)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(0)
        column.addWidget(top)
        column.addWidget(screen, 1)
        column.addWidget(dock)
        return central

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_breakpoint(self.width())
        self._cap_strip()

    def _cap_strip(self) -> None:
        """How much of the column the transport may take before it scrolls."""
        cap = (
            int(self.height() * NARROW_TRANSPORT_SHARE)
            if self._narrow
            else render.UNCONSTRAINED
        )
        if cap != self._strip.maximumHeight():
            self._strip.setMaximumHeight(max(1, cap))
            self._strip.updateGeometry()

    def _apply_breakpoint(self, width: int) -> None:
        """The one breakpoint.

        Qt has no wrapping row, so what CSS would get from `flex-wrap` is
        this: below 760px every group in the transport becomes a row of its
        own. Above it, the groups on a row share a line.
        """
        narrow = width < house.BREAKPOINT

        if narrow == self._narrow:
            return

        self._narrow = narrow
        direction = (
            QHBoxLayout.Direction.TopToBottom
            if narrow
            else QHBoxLayout.Direction.LeftToRight
        )
        for _, layout in self._rows:
            layout.setDirection(direction)
            layout.setSpacing(10 if narrow else 28)

        # The groups turn too, and this is the part that was missing: a group
        # keeps its stretch share of the row however narrow the row gets, so
        # left in one line its controls do not wrap, they clip - "rising" and
        # "falling" came out as "sin" and "llin". One control per line below
        # the breakpoint is a taller strip and a legible one.
        for layout in self._groups:
            layout.setDirection(direction)
            layout.setSpacing(10 if narrow else 22)

        # And the four rows that cannot wrap on their own. Left in one line
        # each, the dock alone set a 654px floor on the window - a page that
        # stops being resizable rather than one that looks wrong, which is
        # the harder kind to notice.
        for row in (self._head, self._readout, self._measurements, self._foot):
            row.set_narrow(narrow)

    # --------------------------------------------------------------- helpers

    def _current_window_ms(self) -> int:
        return round(1000 * self._engine.window_length / self._engine.samplerate)

    def _clamp_window_ms(self, value: int) -> int:
        return max(MIN_WINDOW_MS, min(MAX_WINDOW_MS, int(value)))

    def _sync_labels(self) -> None:
        self._level_value.setText(f"{self._engine.trigger_level:+.3f}")
        self._window_value.setText(f"{self._current_window_ms()} ms")
        self._position_value.setText(f"{round(self._engine.position * 100)}%")
        holdoff = round(self._engine.holdoff_ms)
        self._holdoff_value.setText("off" if holdoff == 0 else f"{holdoff} ms")
        depth = self._renderer.persistence
        self._persistence_value.setText("off" if depth == 0 else f"{depth}")

        arrow = "↑" if self._engine.trigger_edge == "rising" else "↓"
        self._looking.setText(f"{arrow} {self._engine.trigger_level:+.3f}")

        self._run_button.setText(house.caps("stop" if self._running else "run"))

    # ----------------------------------------------------------------- slots

    def _on_level_changed(self, value: int) -> None:
        level = value / LEVEL_SLIDER_SCALE
        self._engine.trigger_level = level
        self._renderer.set_trigger_level(level)
        self._sync_labels()

    def _on_edge_changed(self, index: int) -> None:
        self._engine.trigger_edge = EDGES[index]
        self._sync_labels()

    def _on_window_changed(self, value_ms: int) -> None:
        samples = round(value_ms * self._engine.samplerate / 1000)
        self._engine.window_length = max(MIN_WINDOW, samples)
        self._sync_labels()

    def _on_position_changed(self, percent: int) -> None:
        self._engine.position = percent / 100.0
        self._sync_labels()

    def _on_holdoff_changed(self, value_ms: int) -> None:
        self._engine.holdoff_ms = float(value_ms)
        self._sync_labels()

    def _on_persistence_changed(self, depth: int) -> None:
        self._renderer.persistence = depth
        self._sync_labels()

    def _on_source_changed(self, index: int) -> None:
        self._engine.trigger_source = index

    def _on_display_changed(self, index: int) -> None:
        self._renderer.mode = render.XY if index == 1 else render.YT

    def _on_mode_changed(self, index: int) -> None:
        self._trigger_mode = TRIGGER_MODES[index]
        # Changing mode re-arms: a single that has already fired is a stopped
        # scope, and the setting you just reached for should start it.
        self._caught = False
        self._running = True
        self._sync_labels()

    def _on_run_clicked(self) -> None:
        self._running = not self._running
        if self._running:
            self._caught = False
        self._sync_labels()

    def _on_autoset(self) -> None:
        """Put the signal on screen: enough cycles to see, level in the middle.

        The one control on the page that reads the signal before it sets
        anything. It sets the three knobs a hand would reach for in the same
        order - time, level, noise rejection - and nothing else, so what it
        did stays legible in the controls it moved.
        """
        result = self._engine.capture()
        samples = result.samples
        if samples.size == 0:
            return

        reading = measure.measure(samples, result.samplerate)

        if reading.hz:
            span_ms = 1000.0 * AUTOSET_CYCLES / reading.hz
            self._window_slider.setValue(self._clamp_window_ms(round(span_ms)))

        # Halfway up the signal, not zero: a waveform sitting off centre has
        # its cleanest edge at its own midpoint.
        low, high = float(np.min(samples)), float(np.max(samples))
        midpoint = (high + low) / 2.0
        self._level_slider.setValue(
            int(round(np.clip(midpoint, -1.0, 1.0) * LEVEL_SLIDER_SCALE))
        )

        # A band a twentieth of the signal wide: past the noise, well inside
        # the edge it has to sit on.
        self._engine.hysteresis = max(0.002, 0.05 * reading.vpp)
        self._sync_labels()

    # ----------------------------------------------------------------- loop

    def _on_frame(self) -> None:
        if not self._running:
            return

        result = self._engine.capture()

        if self._trigger_mode == AUTO or result.triggered:
            self._renderer.update(result)
            if self._trigger_mode == SINGLE and result.triggered:
                self._running = False
                self._caught = True
                self._sync_labels()

        self._frames += 1

        now = time.perf_counter()
        elapsed = now - self._last_readout
        if elapsed >= READOUT_INTERVAL:
            self._fps = self._frames / elapsed
            self._frames = 0
            self._last_readout = now
            self._write_readout(result, now)

    def _write_readout(self, result, now: float) -> None:
        """Name the thing. Nothing here tells the person they got it wrong.

        Free run is not a fault - it is a signal with no edge in it, which is
        what silence looks like - so it is said in the colour the house keeps
        for a state nothing has been decided about. Clipping is a fault, and
        is the only thing on this page painted in rust.
        """
        status = self._source.status()
        clipping = result.peak >= CLIP_LEVEL
        xy = self._renderer.mode == render.XY

        if not status.get("running", True):
            self._say("Input stopped.", house.RUST, "no input", "failed")
        elif clipping:
            self._say("Clipping.", house.RUST, "clipping", "failed")
        elif xy and len(result.channels) < 2:
            # Not a fault either: a mono input has no figure to draw, and
            # saying so is kinder than an empty sheet.
            self._say("X-Y needs two channels.", house.UNRESOLVED, "mono input", "ready")
        elif self._caught:
            self._say("Single captured.", house.SAGE, "held", "ready")
        elif result.triggered:
            self._say("Trigger locked.", house.SAGE, "input ready", "ready")
        elif self._engine.holdoff_ms > 0 and result.peak > SILENCE:
            # Holdoff here is a quiet interval *before* an edge, so one set
            # wider than the signal's own period disqualifies every edge there
            # is and the trace goes free. That is the setting doing what it
            # was asked, and it is worth saying which setting did it - the
            # picture is the same as silence and the fix is not.
            self._say("No edge that far apart.", house.UNRESOLVED, "holdoff", "ready")
        elif self._trigger_mode == NORMAL:
            self._say("Waiting for an edge.", house.UNRESOLVED, "armed", "ready")
        elif self._trigger_mode == SINGLE:
            self._say("Armed.", house.UNRESOLVED, "armed", "ready")
        else:
            self._say("Free run.", house.UNRESOLVED, "input ready", "ready")

        # Middots separate, and ampersands do not appear.
        detail = [
            f"peak {result.peak:.3f}",
            f"rms {result.rms:.3f}",
            f"{self._fps:.0f} fps",
        ]
        overflows = status.get("overflows", 0)
        if overflows:
            detail.append(f"{overflows} dropped")

        self._detail.setText(" · ".join(detail))
        self._write_measurements(result)

    def _say(self, verdict: str, colour: str, chip: str, state: str) -> None:
        self._verdict.setText(verdict)
        self._verdict.setStyleSheet(f"color: {colour};")
        self._chip.say(chip, state)

    def _write_measurements(self, result) -> None:
        """Frequency, the note it is, and what sits above it.

        Five times a second, not sixty: an FFT per frame is the one thing on
        this page that would cost the trace its frame rate, and a number that
        changes sixty times a second is a number nobody reads anyway.
        """
        samples = result.samples
        reading = measure.measure(samples, result.samplerate)

        if reading.hz is None:
            self._pitch.setText("—")
        elif reading.note:
            self._pitch.setText(f"{reading.hz:.1f} Hz · {reading.note}")
        else:
            self._pitch.setText(f"{reading.hz:.1f} Hz")

        numbers = [f"vpp {reading.vpp:.3f}"]

        # `dbfs` bottoms out at -inf, and its own docstring says silence is
        # blank on a display rather than a number. Honouring that here is the
        # difference between a quiet scope and a broken-looking one.
        level = measure.dbfs(reading.rms)
        if np.isfinite(level):
            numbers.append(f"{level:.1f} dBFS")
        if reading.period_ms:
            numbers.append(f"{reading.period_ms:.2f} ms")

        harmonics = measure.analyse_harmonics(
            self._harmonic_block(), result.samplerate
        )
        if harmonics is not None:
            numbers.append(f"thd {harmonics.thd * 100:.1f}%")

        numbers.append(f"{result.length} samples")
        self._numbers.setText(" · ".join(numbers))

    def _harmonic_block(self):
        """A block of the live signal long enough to transform honestly.

        Untriggered on purpose: an edge is what makes a *picture* stand still
        and has nothing to do with a spectrum, and asking the trigger for a
        4096-sample window would move the display's own timebase.
        """
        channels = self._source.read(HARMONIC_BLOCK)
        return channels[0] if channels else np.zeros(0, dtype=np.float32)

    # ------------------------------------------------------------- Qt hooks

    def closeEvent(self, event) -> None:
        self._timer.stop()
        try:
            self._source.stop()
        finally:
            super().closeEvent(event)
