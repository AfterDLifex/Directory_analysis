"""
Reusable animation helpers.

Every helper is small and idempotent so widgets can call them from
``showEvent`` / ``set_result`` without leaking animations. All of them respect
Qt's reduced-motion style hint.
"""

from __future__ import annotations

from typing import Callable, Iterable, Optional

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, Qt, QTimer
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect, QScrollArea, QStackedWidget, QWidget,
)

#: Standard durations - kept short so the UI never feels sluggish.
FAST = 140
NORMAL = 220
SLOW = 340

#: Per-item delay used by :func:`stagger_in`.
STAGGER_STEP = 28


def reduced_motion() -> bool:
    """True when the platform asks for reduced motion; anims become no-ops."""
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        return False
    try:
        return float(app.styleHints().animationDurationFactor()) == 0.0
    except (AttributeError, TypeError, ValueError):
        return False


def _ease_out() -> QEasingCurve:
    return QEasingCurve(QEasingCurve.Type.OutCubic)


def _ease_in_out() -> QEasingCurve:
    return QEasingCurve(QEasingCurve.Type.InOutCubic)


def _effect(widget: QWidget) -> QGraphicsOpacityEffect:
    """Return (creating if needed) the widget's opacity effect."""
    effect = widget.graphicsEffect()
    if not isinstance(effect, QGraphicsOpacityEffect):
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
    return effect


def _start(anim: QPropertyAnimation, delay: int) -> None:
    """Start ``anim`` now, or after ``delay`` milliseconds."""
    if delay:
        QTimer.singleShot(delay, anim.start)
    else:
        anim.start()


# ---------------------------------------------------------------------------
# Opacity
# ---------------------------------------------------------------------------

def fade_in(widget: QWidget, duration: int = NORMAL, delay: int = 0,
            start: float = 0.0) -> Optional[QPropertyAnimation]:
    """Fade ``widget`` in from ``start`` to fully opaque."""
    if reduced_motion():
        widget.setVisible(True)
        return None
    effect = _effect(widget)
    effect.setOpacity(start)
    anim = QPropertyAnimation(effect, b"opacity", widget)
    anim.setDuration(duration)
    anim.setStartValue(start)
    anim.setEndValue(1.0)
    anim.setEasingCurve(_ease_out())
    _start(anim, delay)
    return anim


def fade_out(widget: QWidget, duration: int = NORMAL,
             on_finished: Optional[Callable[[], None]] = None
             ) -> Optional[QPropertyAnimation]:
    """Fade ``widget`` out, then hide it and drop the graphics effect."""
    if reduced_motion():
        widget.setVisible(False)
        widget.setGraphicsEffect(None)
        if on_finished:
            on_finished()
        return None
    effect = _effect(widget)
    anim = QPropertyAnimation(effect, b"opacity", widget)
    anim.setDuration(duration)
    anim.setStartValue(effect.opacity())
    anim.setEndValue(0.0)
    anim.setEasingCurve(_ease_in_out())

    def _done() -> None:
        widget.setVisible(False)
        widget.setGraphicsEffect(None)
        if on_finished:
            on_finished()

    anim.finished.connect(_done)
    anim.start()
    return anim


def cross_fade(widget: QWidget, duration: int = NORMAL) -> None:
    """Dip a widget's opacity to refresh content without moving layout."""
    if reduced_motion():
        return
    effect = _effect(widget)
    anim = QPropertyAnimation(effect, b"opacity", widget)
    anim.setDuration(duration)
    anim.setStartValue(1.0)
    anim.setKeyValueAt(0.5, 0.45)
    anim.setEndValue(1.0)
    anim.setEasingCurve(_ease_in_out())
    anim.start()
# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------

def pop_in(widget: QWidget, duration: int = NORMAL, scale: float = 0.94,
           start_delay: int = 0) -> Optional[QPropertyAnimation]:
    """Grow ``widget`` slightly into place, anchored to its centre."""
    if reduced_motion():
        return None
    anim = QPropertyAnimation(widget, b"scale", widget)
    anim.setDuration(duration)
    anim.setStartValue(scale)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve(QEasingCurve.Type.OutBack))
    _start(anim, start_delay)
    return anim


def slide_in(widget: QWidget, offset: int = 12, duration: int = NORMAL,
             horizontal: bool = False, start_delay: int = 0):
    """Slide ``widget`` in from an offset while fading it."""
    if reduced_motion():
        return fade_in(widget, duration, start_delay)
    pos = widget.pos()
    delta = QPoint(-offset, 0) if horizontal else QPoint(0, -offset)
    start = (pos + delta).x() if horizontal else (pos + delta).y()
    end = pos.x() if horizontal else pos.y()
    anim = QPropertyAnimation(widget, b"x" if horizontal else b"y", widget)
    anim.setDuration(duration)
    anim.setStartValue(start)
    anim.setEndValue(end)
    anim.setEasingCurve(_ease_out())
    _start(anim, start_delay)
    fade_in(widget, duration, start_delay)
    return anim


def pulse(widget: QWidget, duration: int = 700) -> Optional[QPropertyAnimation]:
    """Brief attention pulse, used when a value refreshes."""
    if reduced_motion():
        return None
    start = widget.geometry()
    anim = QPropertyAnimation(widget, b"geometry", widget)
    anim.setDuration(duration)
    anim.setStartValue(start)
    anim.setKeyValueAt(0.5, start.adjusted(-2, -2, 2, 2))
    anim.setEndValue(start)
    anim.setEasingCurve(_ease_in_out())
    anim.start()
    return anim


def height_reveal(widget: QWidget, duration: int = SLOW) -> Optional[QPropertyAnimation]:
    """Expand a widget from zero height (inline detail rows)."""
    if reduced_motion():
        return None
    anim = QPropertyAnimation(widget, b"maximumHeight", widget)
    anim.setDuration(duration)
    anim.setStartValue(0)
    anim.setEndValue(widget.sizeHint().height())
    anim.setEasingCurve(_ease_out())
    anim.start()
    fade_in(widget, FAST)
    return anim


def stagger_in(widgets: Iterable[QWidget], duration: int = NORMAL,
               step: int = STAGGER_STEP, horizontal: bool = False) -> None:
    """Fade/slide a row or grid of widgets in one after another."""
    for i, w in enumerate(widgets):
        slide_in(w, offset=10, duration=duration,
                 horizontal=horizontal, start_delay=i * step)


# ---------------------------------------------------------------------------
# Page transitions & containers
# ---------------------------------------------------------------------------

class AnimatedStackedWidget(QStackedWidget):
    """Stacked widget whose pages cross-fade (and nudge) on switch."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._anim: Optional[QPropertyAnimation] = None

    def setCurrentIndex(self, index: int) -> None:  # noqa: N802
        if index < 0 or index >= self.count():
            return
        previous = self.currentIndex()
        if index == previous:
            return

        if self._anim is not None:
            self._anim.stop()
            self._anim = None
        old = self.currentWidget()
        if old is not None:
            old.setGraphicsEffect(None)

        super().setCurrentIndex(index)
        target = self.widget(index)
        if target is None:
            return

        fade_in(target, NORMAL, start=1.0 if reduced_motion() else 0.3)
        if not reduced_motion():
            pos = target.pos()
            anim = QPropertyAnimation(target, b"y", target)
            anim.setDuration(SLOW)
            anim.setStartValue(pos.y() + (10 if index > previous else -10))
            anim.setEndValue(pos.y())
            anim.setEasingCurve(_ease_out())
            self._anim = anim
            anim.start()


def make_scroll(inner: QWidget) -> QScrollArea:
    """A borderless, transparent, resizable scroll area for page bodies."""
    scroll = QScrollArea()
    scroll.setObjectName("PageScroll")
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QScrollArea.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setWidget(inner)
    return scroll
# ---------------------------------------------------------------------------
# Numeric counters
# ---------------------------------------------------------------------------

def count_up(label: QWidget, target: str, duration: int = 700,
             on_done: Optional[Callable[[], None]] = None) -> None:
    """Animate a numeric label toward ``target``.

    Only the leading numeric run is animated, so pre-formatted values such as
    ``"4.2 GB"``, ``"1,204"`` or ``"87/100"`` all work; anything non-numeric is
    simply cross-faded in.
    """
    text = str(target).strip()
    digits = ""
    for ch in text:
        if ch.isdigit() or ch in ".,":
            digits += ch
        else:
            break
    suffix = text[len(digits):]

    def _finish() -> None:
        label.setText(target)
        if on_done:
            on_done()

    if not digits or reduced_motion():
        _finish()
        return

    raw = digits.replace(",", "")
    try:
        number = float(raw)
    except ValueError:
        _finish()
        return

    decimals = len(raw.split(".")[1]) if "." in raw else 0
    use_commas = "," in digits
    frames = 18
    interval = max(1, duration // frames)

    def _tick(value: float) -> None:
        body = f"{value:,.{decimals}f}" if use_commas else f"{value:.{decimals}f}"
        label.setText(body + suffix)

    _tick(number)
    cross_fade(label, FAST)
    counter = {"n": 0}

    def _step() -> None:
        counter["n"] += 1
        t = min(counter["n"] / frames, 1.0)
        _tick(number * (1 - pow(1 - t, 3)))
        if t < 1:
            QTimer.singleShot(interval, _step)
        else:
            _finish()

    QTimer.singleShot(interval, _step)
