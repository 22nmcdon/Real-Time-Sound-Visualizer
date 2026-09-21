"""The house style, as one block of tokens.

`BRANDING.md` is the source; this is its drop-in block in the one form a Qt
app can read. The rule that document leads with is the rule here: a colour
written as a literal is a colour that will not follow the light, so nothing
below this file spells a hex digit.

Three things the web surface gets for free and this one has to do by hand:

- **Qt has no `text-transform` and no `letter-spacing` in its stylesheet
  language.** The small-caps control is most of the page's character, so it
  is not optional - it is done in Python instead, by `small_caps()` on the
  font and `.upper()` on the string.
- **Qt has no `:focus-visible`, only `:focus`** - so a plain `:focus` rule
  rings the first control on the page the moment the window opens, which is
  not what the web surface does and looks like something is already wrong.
  `FocusVisible` below puts it back: Qt hands every focus event a *reason*,
  and Tab, Backtab and a shortcut are exactly the three that mean a keyboard.
- **A radius of `50%` is not a thing here.** A dot is drawn at half its own
  pixel size, which is the same circle by arithmetic.
"""

from __future__ import annotations

from PyQt6.QtCore import QEvent, QObject, QRectF, Qt
from PyQt6.QtGui import (
    QColor,
    QFontMetricsF,
    QFont,
    QFontMetrics,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRegion,
)
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

# --- colour ----------------------------------------------------------------
# The default light. There is one here, where the jazz page has two, because
# this surface has one mode - but the components below read tokens and name no
# colour of their own, so a second light stays a dict swap rather than a
# restyle. That is the whole point of the token layer.

CREAM = "#faf6f0"        # the page
CREAM_2 = "#f2ebe1"      # the dock, and anything sitting under the page
PAPER = "#fffcf7"        # the sheet itself, and every input
CHARCOAL = "#241f1d"     # ink - never pure black
TEXT = "#3a332f"
TEXT_SOFT = "#6b615a"
LINE = "#e4d9cc"         # every border and rule
BLUSH = "#d9a6a0"        # the accent at rest
BLUSH_DEEP = "#c07f79"   # the accent doing work
GOLD = "#b08d57"         # ready

# The five that never move.  Each says one thing, so each is used here only
# where this surface means that same thing:
#
#   sage        the trigger locked - "this matches"
#   unresolved  free run - open, undecided.  Deliberately NOT rust: a signal
#               with no edge in it is not a fault, and the quietest colour of
#               the set is the one that does not read as a verdict.
#   rust        clipping, and a dropped block - both of them actual problems
#
# `approach` and `enclosure` have nothing to mean on an oscilloscope, so
# nothing here is painted in them.  They stay defined rather than deleted:
# they are part of the block, and a later surface that borrows this file
# should find the five intact rather than three and a gap.
SAGE = "#6f7f63"
APPROACH = "#8fae6d"
ENCLOSURE = "#3f8f88"
RUST = "#a4553f"
UNRESOLVED = "#b6afa4"

# The accent laid over something - hover, then selection. Tokens rather than
# an rgba() at the call site, for the reason above.
WASH = "rgba(217, 166, 160, 0.16)"
WASH_STRONG = "rgba(217, 166, 160, 0.26)"

# The sheet's shadow, as its two parts. Spelled here so `Sheet` below paints
# what the stylesheet would have.
SHADOW_INK = (36, 31, 29)
SHADOW_ALPHA = 0.06
SHADOW_DROP = 14         # px down
SHADOW_BLUR = 34         # px of spread

# --- type ------------------------------------------------------------------
# Fallbacks in every stack, and they are not a formality: none of the four
# brand faces is installed on a machine that has not been given them, so the
# stack below is what most runs of this app actually render in.

SERIF = ["Playfair Display", "Georgia", "Times New Roman", "serif"]
SCRIPT = ["Cormorant Garamond", "Georgia", "serif"]
SANS = ["Jost", "Segoe UI", "DejaVu Sans", "Helvetica Neue", "sans-serif"]
MONO = ["Menlo", "Consolas", "DejaVu Sans Mono", "monospace"]

# `--hand` is chord symbols and only chord symbols.  There are no chord
# symbols on an oscilloscope, so this surface sets nothing in it - the stack
# is kept so the omission reads as a decision rather than an oversight.
HAND = ["Kalam", "Bradley Hand", "Segoe Print", "cursive"]

BODY_SIZE = 16
BODY_WEIGHT = 300
BODY_LEADING = 1.65

EYEBROW_SIZE = 11
EYEBROW_TRACKING = 0.28   # em
CONTROL_SIZE = 10.5
CONTROL_TRACKING = 0.18   # em
HEADING_TRACKING = 0.01   # em

# --- shape -----------------------------------------------------------------
# Exactly three radii, and each one means something.
RADIUS_PAPER = 1          # inputs, selects, filled buttons
RADIUS_STATE = 30         # a mode or a state: pills
RADIUS_CHIP = 20          # a small pill
# A dot is `50%`, which Qt cannot say; `dot_radius()` says it in pixels.

BORDER = 1                # 1px solid --line, almost everywhere
BARLINE = 2               # the two exceptions: a barline, and a finding's rule

# --- layout ----------------------------------------------------------------
MAX_WIDTH = 1080
GUTTER = 24               # padding-inline
BREAKPOINT = 760          # the one breakpoint
MEASURE = 62              # ch, for ledes and findings
RESERVED_ROW = 46         # px: anything that reserves height, reserves it always

# --- motion ----------------------------------------------------------------
# Almost nothing moves, which is what lets the things that do move work. Qt
# has no CSS transitions, so what the web page gets from one line of CSS is
# either animated by hand here or not at all. Only the breathing one is worth
# hand-animating: it is load-bearing rather than decorative.
BREATHE_MS = 1300         # an open, undecided state
BREATHE_FLOOR = 0.45      # what it fades to


def dot_radius(size: int) -> int:
    """`border-radius: 50%`, in the pixels Qt wants instead."""
    return size // 2


def tokens() -> dict:
    """Every token by its stylesheet name, for formatting into the QSS."""
    return {
        "cream": CREAM,
        "cream2": CREAM_2,
        "paper": PAPER,
        "charcoal": CHARCOAL,
        "text": TEXT,
        "textSoft": TEXT_SOFT,
        "line": LINE,
        "blush": BLUSH,
        "blushDeep": BLUSH_DEEP,
        "gold": GOLD,
        "sage": SAGE,
        "rust": RUST,
        "unresolved": UNRESOLVED,
        "wash": WASH,
        "washStrong": WASH_STRONG,
        "radiusPaper": RADIUS_PAPER,
        "radiusState": RADIUS_STATE,
        "border": BORDER,
        "bodySize": BODY_SIZE,
        "gutter": GUTTER,
    }


# Qt reads a subset of CSS, so this is the page's stylesheet minus everything
# Qt has no word for. What is missing is made up in `fonts.py`-worth of helpers
# at the bottom of this file rather than being quietly dropped.
STYLE_SHEET = """
QWidget {{
    background: {cream};
    color: {text};
}}

QLabel {{ background: transparent; }}

/* The sheet, and anything sitting under the page. */
#sheet {{ background: {paper}; }}
#dock  {{ background: {cream2}; border-top: {border}px solid {line}; }}
#topBar {{ background: {cream}; border-bottom: {border}px solid {line}; }}

/* --- buttons come in three weights -------------------------------------- */

/* Filled: the primary action of a section, and at most one per section. */
QPushButton[weight="filled"] {{
    background: {charcoal};
    color: {cream};
    border: {border}px solid {charcoal};
    border-radius: {radiusPaper}px;
    padding: 7px 15px;
}}
QPushButton[weight="filled"]:hover:!disabled {{
    background: {blushDeep};
    border-color: {blushDeep};
}}
QPushButton[weight="filled"]:disabled {{ color: {line}; }}

/* Outlined pill: a mode or a menu - something you are in, not something you do. */
QPushButton[weight="pill"] {{
    background: transparent;
    border: {border}px solid {line};
    border-radius: {radiusState}px;
    padding: 6px 15px;
    color: {charcoal};
}}
QPushButton[weight="pill"]:hover {{ border-color: {blush}; color: {blushDeep}; }}
QPushButton[weight="pill"][chosen="true"] {{
    background: {charcoal};
    border-color: {charcoal};
    color: {cream};
}}

/* Underlined: no box at all. A pressed state thickens the rule rather than
   filling anything, because it is a state and not an action. */
QPushButton[weight="link"] {{
    background: transparent;
    border: none;
    border-bottom: {border}px solid {blush};
    padding: 0 0 2px;
    color: {charcoal};
}}
QPushButton[weight="link"]:hover {{ color: {blushDeep}; border-bottom-color: {blushDeep}; }}
QPushButton[weight="link"][chosen="true"] {{
    color: {blushDeep};
    border-bottom: {border}px solid {blushDeep};
}}

/* Paper: an input is a sheet, so it is square. */
QSpinBox, QDoubleSpinBox, QComboBox {{
    background: {paper};
    border: {border}px solid {line};
    border-radius: {radiusPaper}px;
    padding: 4px 7px;
    color: {charcoal};
}}
QComboBox QAbstractItemView {{
    background: {paper};
    border: {border}px solid {line};
    color: {charcoal};
    selection-background-color: {washStrong};
    selection-color: {charcoal};
}}

/* The slider's groove is a rule on the page; its handle is a dot. */
QSlider::groove:horizontal {{
    height: 2px;
    background: {line};
}}
QSlider::handle:horizontal {{
    background: {blushDeep};
    width: 13px;
    height: 13px;
    margin: -6px 0;
    border-radius: 6px;
}}
QSlider::handle:horizontal:hover {{ background: {charcoal}; }}
QSlider::sub-page:horizontal {{ background: {blush}; height: 2px; }}

/* 2px solid --blush-deep, everywhere - but only for a keyboard, which is
   what `FocusVisible` decides. Qt has no `outline`, so this is a border and
   the offset the house asks for is not available. */
*[kbd="true"]:focus {{
    outline: none;
    border: 2px solid {blushDeep};
}}

/* The switch: two sides of one thing, in a pill. Qt will not clip a child to
   its parent's radius, so the chosen side is itself a pill inside the frame
   rather than a filled rectangle with the corners cut off it. */
#switchFrame {{
    background: transparent;
    border: {border}px solid {line};
    border-radius: {radiusState}px;
}}
QPushButton[weight="switch"] {{
    background: transparent;
    border: none;
    border-radius: {radiusState}px;
    padding: 6px 15px;
    color: {textSoft};
}}
QPushButton[weight="switch"]:hover {{ color: {blushDeep}; }}
QPushButton[weight="switch"][chosen="true"] {{
    background: {charcoal};
    color: {cream};
}}

/* The status chip, and the legend dots. A chip is a state you are in, so it
   is a pill; a dot is a dot. */
QLabel[weight="chip"] {{
    border: {border}px solid {line};
    border-radius: {radiusState}px;
    padding: 5px 14px;
    color: {textSoft};
}}
QLabel[weight="chip"][state="ready"] {{ color: {gold}; border-color: {gold}; }}
QLabel[weight="chip"][state="failed"] {{ color: {rust}; border-color: {rust}; }}

/* A scrollbar is a rule with a dot on it, the same way a slider is - it is
   the one piece of Qt chrome the house cannot restyle out of existence, so
   it is restyled into the furniture instead. */
QScrollArea {{ background: transparent; border: none; }}
QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {line};
    border-radius: 3px;
    min-height: 26px;
}}
QScrollBar::handle:vertical:hover {{ background: {blush}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
    width: 0;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}

QToolTip {{
    background: {paper};
    color: {text};
    border: {border}px solid {line};
    padding: 4px 7px;
}}
"""


def style_sheet() -> str:
    return STYLE_SHEET.format(**tokens())


class FocusVisible(QObject):
    """`:focus-visible`, built out of the reason Qt gives for a focus change.

    Install it on the application once. Every widget that takes focus is
    tagged `kbd="true"` or `kbd="false"` on the way in, and the stylesheet
    rings only the first kind - so tabbing through the page shows where you
    are and clicking a slider does not draw a box round it.
    """

    _KEYBOARD = (
        Qt.FocusReason.TabFocusReason,
        Qt.FocusReason.BacktabFocusReason,
        Qt.FocusReason.ShortcutFocusReason,
    )

    def eventFilter(self, watched, event):
        # Installed on the application, so everything Qt owns comes through
        # here - the top-level `QWindow` and the style object among them, and
        # neither has a style to repolish. Without the guard the first Tab
        # raises inside an event filter, where Qt prints the traceback and
        # carries on, so the only symptom is a focus ring that never appears.
        if event.type() == QEvent.Type.FocusIn and isinstance(watched, QWidget):
            watched.setProperty(
                "kbd", "true" if event.reason() in self._KEYBOARD else "false"
            )
            restyle(watched)

        return False


def watch_focus(app) -> FocusVisible:
    """Turn `:focus-visible` on for an application.

    The filter is parented to the app, so Qt's ownership keeps it alive; a
    filter that is garbage collected stops filtering and the only symptom is
    that the focus ring quietly stops appearing.
    """
    guard = FocusVisible(app)
    app.installEventFilter(guard)
    return guard


# A box layout shares space out by stretch factor and has no idea what a
# max-width is, so the middle of `wrap` has to out-vote the two margins by
# enough that what it loses to them rounds away. Written 1/1/1 - which looks
# like the obvious thing - it gives the content a third of the window. Public
# because the X-Y stage needs the same trick.
FILL = 1_000_000


def wrap(inner, gutter: int = GUTTER):
    """`max-width: 1080px; margin: 0 auto; padding-inline: 24px`.

    Every zone's contents go through here, which is what keeps the head, the
    screen and the dock in one column on a wide monitor instead of each
    finding its own edges. Past `--max` the margins take the difference;
    below it they take nothing and the content runs to the gutters.
    """
    inner.setMaximumWidth(MAX_WIDTH)

    holder = QWidget()
    row = QHBoxLayout(holder)
    row.setContentsMargins(gutter, 0, gutter, 0)
    row.addStretch(1)
    row.addWidget(inner, FILL)
    row.addStretch(1)
    return holder


def restyle(widget) -> None:
    """Make Qt notice a dynamic property that a selector reads.

    A stylesheet rule keyed on `[chosen="true"]` is matched once, when the
    widget is polished - setting the property afterwards changes nothing on
    screen until the style is asked to look again. Every switch and chip
    below goes through here, which is why none of them sets a colour itself.
    """
    widget.style().unpolish(widget)
    widget.style().polish(widget)


# --- the two mannerisms Qt cannot state in a stylesheet --------------------
# The eyebrow and the small-caps control carry most of the page's character,
# so neither is allowed to quietly not happen. Both are built here.


_WEIGHTS = {
    300: QFont.Weight.Light,
    400: QFont.Weight.Normal,
    500: QFont.Weight.Medium,
    600: QFont.Weight.DemiBold,
    700: QFont.Weight.Bold,
}


def font(stack, size, weight=400, tracking=0.0) -> QFont:
    """A face from one of the stacks above.

    ``size`` is in px and ``tracking`` in em, which is how `BRANDING.md`
    states them.  Qt only takes a whole number of pixels, so 10.5px renders
    at 11 - half a pixel, and the alternative is mixing points into a
    document written in pixels throughout.
    """
    chosen = QFont()
    chosen.setFamilies(list(stack))
    chosen.setPixelSize(int(size + 0.5))
    chosen.setWeight(_WEIGHTS.get(weight, QFont.Weight.Normal))

    if tracking:
        # Absolute rather than percentage: tracking is quoted in em against
        # this size, and a percentage would be against the face's own idea of
        # a space - which differs between the brand faces and the fallbacks.
        chosen.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, tracking * size)

    return chosen


def body_font(size=BODY_SIZE, weight=BODY_WEIGHT) -> QFont:
    return font(SANS, size, weight)


def heading_font(size) -> QFont:
    return font(SERIF, size, 600, HEADING_TRACKING)


def credit_font(size=14) -> QFont:
    """The script face, italic only - it is never set upright."""
    chosen = font(SCRIPT, size, 500)
    chosen.setItalic(True)
    return chosen


def mono_font(size=12) -> QFont:
    return font(MONO, size, 400)


def control_font(tracking=CONTROL_TRACKING) -> QFont:
    """The small-caps control: 10.5px, wide-tracked, weight 500.

    Nothing on this page shouts in large type; it whispers in wide-tracked
    small type instead. Pair it with `caps()` on the string - Qt has no
    `text-transform`, so a control set in this face and given a
    sentence-case label is only half of the mannerism.
    """
    return font(SANS, CONTROL_SIZE, 500, tracking)


def caps(text: str) -> str:
    """The other half of the small-caps control."""
    return text.upper()


def measure_px(chosen: QFont, chars=MEASURE) -> int:
    """A measure capped in `ch`, in the pixels a widget needs instead."""
    return QFontMetrics(chosen).horizontalAdvance("0") * chars


def eyebrow(text: str) -> QLabel:
    """11px, uppercase, 0.28em, --blush-deep, weight 500.

    It sits above a heading or labels a field, and it is the one piece of
    type on the page allowed to be that widely tracked.
    """
    label = QLabel(caps(text))
    label.setFont(font(SANS, EYEBROW_SIZE, 500, EYEBROW_TRACKING))
    label.setStyleSheet(f"color: {BLUSH_DEEP};")
    return label


class Elide(QLabel):
    """A label that shortens rather than pushing the page wider.

    The credit is the first thing on this page that can run out of room -
    nothing else here is ever long enough to need it - and a device with a
    long name must not be what shoves the status chip off the side. Qt has no
    `text-overflow`, so the ellipsis is put in at paint time and the full text
    stays on the tooltip.
    """

    def __init__(self, text: str = ""):
        super().__init__(text)
        self._full = text
        self.setMinimumWidth(0)
        self.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )

    def setText(self, text: str) -> None:
        self._full = text
        self.setToolTip(text)
        super().setText(text)

    def paintEvent(self, event):
        metrics = QFontMetricsF(self.font())
        shown = metrics.elidedText(
            self._full, Qt.TextElideMode.ElideRight, self.width()
        )
        painter = QPainter(self)
        try:
            painter.setFont(self.font())
            painter.setPen(self.palette().color(self.foregroundRole()))
            painter.drawText(self.rect(), int(self.alignment()), shown)
        finally:
            painter.end()


class Reflow(QWidget):
    """One row above the breakpoint, two rows below it.

    Qt has no `flex-wrap`, so a row of controls that fits a laptop simply
    refuses to be narrower than its contents - it does not wrap, it sets the
    window's minimum width and the page stops being resizable at all. That is
    how the dock came to be 654px wide at the bottom of a 430px window.

    `lead` keeps the first line; `trail` joins it when there is room and drops
    to a line of its own when there is not.
    """

    def __init__(self, lead, trail, spacing=14, gap=6):
        super().__init__()
        self._lead = list(lead)
        self._trail = list(trail)
        self._narrow = None

        # A reflowing row must not set a floor under the window. Qt clamps a
        # resize to the layout's current minimum, so a row still in its wide
        # state would refuse the very resize that is about to narrow it - the
        # window jumps to 654px and no further, and the reflow never runs.
        # Ignored means "give me what is going", which is the honest request
        # from something that rearranges to fit.
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setMinimumWidth(0)

        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(gap)

        self._row1, self._line1 = self._row(spacing)
        self._row2, self._line2 = self._row(spacing)
        column.addWidget(self._row1)
        column.addWidget(self._row2)

        self.set_narrow(False)

    @staticmethod
    def _row(spacing):
        holder = QWidget()
        line = QHBoxLayout(holder)
        line.setContentsMargins(0, 0, 0, 0)
        line.setSpacing(spacing)
        return holder, line

    def set_narrow(self, narrow: bool) -> None:
        if narrow == self._narrow:
            return

        self._narrow = narrow

        # Rebuilt rather than shuffled. It happens twice in the life of a
        # window - once each way across the breakpoint - so the cost is
        # nothing and the alternative is bookkeeping about where the stretch
        # currently is.
        for line in (self._line1, self._line2):
            while line.count():
                line.takeAt(0)

        if narrow:
            self._fill(self._line1, self._lead)
            self._fill(self._line2, self._trail)
            self._row2.show()
        else:
            self._fill(self._line1, self._lead + self._trail)
            self._row2.hide()

    @staticmethod
    def _fill(line, widgets) -> None:
        """Lay a row out, giving the slack to whatever asked for it.

        A widget whose policy is Ignored or Expanding is the row's `flex: 1` -
        the eliding credit, which should take the room that is going and
        shorten when there is none. Added at stretch 0 like the rest, it gets
        nothing at all and elides to the empty string, which is how the device
        name vanished at 430px rather than shortening.
        """
        hungry = [
            widget
            for widget in widgets
            if widget.sizePolicy().horizontalPolicy()
            in (QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        ]

        for widget in widgets:
            line.addWidget(widget, 1 if widget in hungry else 0)

        # Only when nothing in the row will take it: an expanding widget is
        # already holding the row open, and a stretch beside it would split
        # the slack with the thing that asked for it.
        if not hungry:
            line.addStretch(1)


class Sheet(QFrame):
    """The lead sheet: paper, one stop brighter than the page, on a desk.

    The one component the design system itself provides, because it is the
    one place depth is used - `0 1px 0 --cream-2, 0 14px 34px rgba(ink, .06)`,
    and nothing else on the page floats.

    Qt's own drop shadow is `QGraphicsDropShadowEffect`, and it is the wrong
    tool here: an effect renders its widget into an offscreen pixmap on every
    repaint, and the child of this one repaints sixty times a second.

    Painting it by hand is not enough on its own either.  The assumption that
    an opaque child does not damage its parent is wrong for a `QGraphicsView`,
    which is what the plot is: this ran **once per frame**, and ten rounded
    fills at that rate took 57 fps down to 23.  So the rings are rendered into
    a pixmap once and blitted after that, and the blit is clipped to the band
    around the child, because the middle of it is behind an opaque widget and
    was being drawn for nobody.

    Measure before changing any of this.  The look is four lines of CSS on the
    web page and the cost of it there is nothing; here it is the second most
    expensive thing on the screen.
    """

    def __init__(self, child: QWidget, parent=None):
        super().__init__(parent)
        self.setObjectName("sheet")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        # The margin is the shadow's own room. Without it the blur would be
        # painted underneath the child and never seen.
        room = SHADOW_BLUR // 2   # the shadow's room; the 1px border sits inside it
        layout = QVBoxLayout(self)
        layout.setContentsMargins(room, room, room, room + SHADOW_DROP // 2)
        layout.addWidget(child)

        self._child = child
        self._shadow = None      # rendered on demand, thrown away on resize

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._shadow = None

    def _render_shadow(self) -> QPixmap:
        """The rings, once, into a pixmap the frames can blit."""
        shadow = QPixmap(self.size() * self.devicePixelRatioF())
        shadow.setDevicePixelRatio(self.devicePixelRatioF())
        shadow.fill(Qt.GlobalColor.transparent)

        painter = QPainter(shadow)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

            # QRectF, because the rings are spread by fractions of a pixel and
            # QRect rounds - the shadow is the one thing here drawn off the
            # pixel grid on purpose.
            frame = QRectF(self._child.geometry())

            # Ten rings is enough that the gradient does not band at this spread.
            rings = 10
            for step in range(rings, 0, -1):
                spread = SHADOW_BLUR * step / rings
                ink = QColor(*SHADOW_INK)
                ink.setAlphaF(SHADOW_ALPHA * (1 - step / (rings + 1)) / 2)

                path = QPainterPath()
                path.addRect(
                    frame.adjusted(
                        -spread,
                        -spread + SHADOW_DROP / 2,
                        spread,
                        spread + SHADOW_DROP / 2,
                    )
                )
                painter.fillPath(path, ink)

            # And the hard 1px lip underneath, which is what makes it a sheet
            # laid on a desk rather than one hovering above it.
            painter.fillRect(frame.adjusted(0, 1, 0, 1), QColor(CREAM_2))
            painter.fillRect(frame, QColor(PAPER))

            # The paper's edge. Drawn just outside the child, so it lands in
            # the band this widget still paints rather than under the plot.
            painter.setPen(QPen(QColor(LINE), BORDER))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(frame.adjusted(-0.5, -0.5, 0.5, 0.5))
        finally:
            painter.end()

        return shadow

    def paintEvent(self, event):
        if self._shadow is None:
            self._shadow = self._render_shadow()

        painter = QPainter(self)
        try:
            # Everything but the rectangle the plot is about to paint over.
            # That rectangle is most of this widget, and blitting it sixty
            # times a second so an opaque child can cover it is the whole of
            # what made this expensive.
            painter.setClipRegion(
                QRegion(self.rect()) - QRegion(self._child.geometry())
            )
            painter.drawPixmap(0, 0, self._shadow)
        finally:
            # Without this a raise here leaves the painter active on the
            # backing store, and every later repaint fails too - one bug
            # reported as forty.
            painter.end()
