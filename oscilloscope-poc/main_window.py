"""The frame: a head, the screen, and a dock. Nothing scrolls but the middle.

Three zones, as the house lays a page out. The head is furniture at its own
height, the dock is furniture at its own height, and the screen takes every
pixel the other two do not - so anything added to the head or the dock is
taken out of the trace and has to earn it.

The strip under the head is the transport. What is on it is what you reach
for while the signal is running: where the trigger sits, which way through it
the signal has to be going, and how much time is on screen. It is two groups,
and each is one row of its own at any width - which is what keeps the top of
the screen from moving when the window narrows.
"""

from __future__ import annotations

import time

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

import branding as house
from renderer import ScopeRenderer
from trigger import EDGES, MIN_WINDOW

LEVEL_SLIDER_SCALE = 1000   # slider ticks per unit of amplitude
MIN_WINDOW_MS = 2
MAX_WINDOW_MS = 200         # well inside the engine's own 1 s ceiling

# Slower than the frame rate, because the readout is read rather than watched:
# words changing sixty times a second are words nobody finishes.
READOUT_INTERVAL = 0.2

# A sample at full scale is a sample the converter may have clipped.
CLIP_LEVEL = 0.999

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

        self.setWindowTitle("Oscilloscope")
        self.setStyleSheet(house.style_sheet())
        self.resize(1100, 660)

        self._renderer = ScopeRenderer(samplerate=engine.samplerate)
        self._renderer.set_trigger_level(engine.trigger_level)

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
        self._level_slider = QSlider(Qt.Orientation.Horizontal)
        self._level_slider.setRange(-LEVEL_SLIDER_SCALE, LEVEL_SLIDER_SCALE)
        self._level_slider.setValue(round(self._engine.trigger_level * LEVEL_SLIDER_SCALE))
        self._level_slider.valueChanged.connect(self._on_level_changed)
        self._level_value = self._reading_label()

        self._edge_switch = Switch(
            [edge for edge in EDGES],
            chosen=EDGES.index(self._engine.trigger_edge),
            on_change=self._on_edge_changed,
        )

        self._window_slider = QSlider(Qt.Orientation.Horizontal)
        self._window_slider.setRange(MIN_WINDOW_MS, MAX_WINDOW_MS)
        self._window_slider.setValue(self._clamp_window_ms(self._current_window_ms()))
        self._window_slider.valueChanged.connect(self._on_window_changed)
        self._window_value = self._reading_label()

        # Two groups, each one row of its own at any width. The level slider
        # wants room and the edge switch does not, so they share a line; the
        # timebase is the other. Split the other way and the wide control and
        # the narrow one end up on the same line as each other twice over.
        self._trigger_group = QWidget()
        trigger = QHBoxLayout(self._trigger_group)
        trigger.setContentsMargins(0, 0, 0, 0)
        trigger.setSpacing(22)
        trigger.addWidget(Field("trigger level", self._level_slider, self._level_value), 1)
        trigger.addWidget(Field("edge", self._edge_switch))

        self._timebase_group = QWidget()
        timebase = QHBoxLayout(self._timebase_group)
        timebase.setContentsMargins(0, 0, 0, 0)
        timebase.setSpacing(22)
        timebase.addWidget(Field("window", self._window_slider, self._window_value), 1)

        # Same reason as `Reflow`: the transport rearranges to fit, so it
        # must not be what stops the window fitting.
        for group in (self._trigger_group, self._timebase_group):
            group.setSizePolicy(
                QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
            )
            group.setMinimumWidth(0)

        self._transport = QWidget()
        self._transport_layout = QHBoxLayout(self._transport)
        self._transport_layout.setContentsMargins(0, 0, 0, 0)
        self._transport_layout.setSpacing(28)
        self._transport_layout.addWidget(self._trigger_group, 2)
        self._transport_layout.addWidget(self._timebase_group, 1)

        # None rather than False, so the first call always applies a state -
        # a window opened narrow must reflow before it is shown, or its own
        # minimum width holds it wide and no resize can get it back.
        self._narrow = None

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

        self._foot = house.Reflow(
            lead=[
                self._legend(house.CHARCOAL, "locked"),
                self._legend(house.UNRESOLVED, "free run"),
                self._legend(house.BLUSH_DEEP, "trigger level"),
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
            f"{status.get('channels', self._source.channels)} ch",
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
        stacked.setSpacing(10)
        stacked.addWidget(self._head)
        stacked.addWidget(self._transport)

        top_column = QVBoxLayout(top)
        top_column.setContentsMargins(0, 10, 0, 10)
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

    def _apply_breakpoint(self, width: int) -> None:
        """The one breakpoint.

        Qt has no wrapping row, so what CSS would get from `flex-wrap` is
        this: below 760px the transport's two groups become a column, each
        still one row of its own. Above it they share a line.
        """
        narrow = width < house.BREAKPOINT

        if narrow == self._narrow:
            return

        self._narrow = narrow
        self._transport_layout.setDirection(
            QHBoxLayout.Direction.TopToBottom if narrow else QHBoxLayout.Direction.LeftToRight
        )
        self._transport_layout.setSpacing(10 if narrow else 28)

        # And the three rows that cannot wrap on their own. Left in one line
        # each, the dock alone set a 654px floor on the window - a page that
        # stops being resizable rather than one that looks wrong, which is
        # the harder kind to notice.
        for row in (self._head, self._readout, self._foot):
            row.set_narrow(narrow)

    # --------------------------------------------------------------- helpers

    def _current_window_ms(self) -> int:
        return round(1000 * self._engine.window_length / self._engine.samplerate)

    def _clamp_window_ms(self, value: int) -> int:
        return max(MIN_WINDOW_MS, min(MAX_WINDOW_MS, int(value)))

    def _sync_labels(self) -> None:
        self._level_value.setText(f"{self._engine.trigger_level:+.3f}")
        self._window_value.setText(
            f"{self._current_window_ms()} ms · {self._engine.window_length} samples"
        )
        arrow = "↑" if self._engine.trigger_edge == "rising" else "↓"
        self._looking.setText(f"{arrow} {self._engine.trigger_level:+.3f}")

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

    def _on_frame(self) -> None:
        result = self._engine.capture()
        self._renderer.update_trace(result.samples, result.triggered)
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

        if not status.get("running", True):
            self._verdict.setText("Input stopped.")
            self._verdict.setStyleSheet(f"color: {house.RUST};")
            self._chip.say("no input", "failed")
        elif clipping:
            self._verdict.setText("Clipping.")
            self._verdict.setStyleSheet(f"color: {house.RUST};")
            self._chip.say("clipping", "failed")
        elif result.triggered:
            self._verdict.setText("Trigger locked.")
            self._verdict.setStyleSheet(f"color: {house.SAGE};")
            self._chip.say("input ready", "ready")
        else:
            self._verdict.setText("Free run.")
            self._verdict.setStyleSheet(f"color: {house.UNRESOLVED};")
            self._chip.say("input ready", "ready")

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

    # ------------------------------------------------------------- Qt hooks

    def closeEvent(self, event) -> None:
        self._timer.stop()
        try:
            self._source.stop()
        finally:
            super().closeEvent(event)
