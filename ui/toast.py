"""
Non-blocking toast notifications.

Toasts stack bottom-right, animate in and out, and auto-dismiss. They are
``WA_TransparentForMouseEvents`` so they can never be the reason a click
appears to "do nothing".
"""

from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, Qt, QTimer
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect, QLabel, QVBoxLayout, QWidget,
)

from .animations import NORMAL, reduced_motion

#: Default lifetime per severity, in milliseconds.
DURATIONS = {"success": 2800, "info": 2600, "warning": 3800, "error": 5200}


class _Toast(QLabel):
    """One toast line; the public API is intentionally tiny."""

    def __init__(self, text: str, kind: str) -> None:
        super().__init__(text)
        self.setObjectName("Toast")
        self.setProperty("toastKind", kind)
        self.setWordWrap(True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._fade: Optional[QPropertyAnimation] = None
        self._timer: Optional[QTimer] = None
        self.resize(self.sizeHint())


class ToastHost(QWidget):
    """Owns, stacks and animates toasts for a parent window."""

    MIN_WIDTH = 260
    MAX_WIDTH = 420

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self._parent = parent
        self._active: List[_Toast] = []
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(8)
        self.setFixedSize(1, 1)

    # -- public API --------------------------------------------------------

    def show(self, text: str, kind: str = "info",
             ms: Optional[int] = None) -> None:
        """Queue a toast; the oldest is dropped past five stacked."""
        kind = kind if kind in DURATIONS else "info"
        toast = _Toast(text, kind)
        toast.setFixedWidth(self._width_for(toast))

        self._layout.addWidget(toast)
        self._active.append(toast)
        self._reposition()
        self._fade(toast, 0.0, 1.0)

        timer = QTimer(toast)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: self.dismiss(toast))
        timer.start(ms or DURATIONS[kind])
        toast._timer = timer          # keep a reference alive on the child

        if len(self._active) > 5:
            self.dismiss(self._active[0])

    def dismiss(self, toast: _Toast) -> None:
        """Fade one toast out and dispose of it."""
        if toast not in self._active:
            return
        self._fade(toast, toast.graphicsEffect().opacity()
                   if isinstance(toast.graphicsEffect(), QGraphicsOpacityEffect)
                   else 1.0, 0.0, on_end=lambda: self._remove(toast))

    def clear(self) -> None:
        """Remove every visible toast immediately."""
        for toast in list(self._active):
            self._remove(toast)

    def on_parent_resize(self) -> None:
        """Keep the stack pinned to the bottom-right corner."""
        self._reposition()

    # -- internals ---------------------------------------------------------

    @classmethod
    def _width_for(cls, toast: _Toast) -> int:
        return min(max(toast.sizeHint().width() + 30, cls.MIN_WIDTH),
                   cls.MAX_WIDTH)

    def _fade(self, toast: _Toast, start: float, end: float,
              on_end: Optional[callable] = None) -> None:
        effect = toast.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(toast)
            toast.setGraphicsEffect(effect)
        effect.setOpacity(start)
        if reduced_motion():
            effect.setOpacity(end)
            if on_end:
                on_end()
            return
        anim = QPropertyAnimation(effect, b"opacity", toast)
        anim.setDuration(NORMAL)
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.setEasingCurve(QEasingCurve(
            QEasingCurve.Type.OutCubic if end > start
            else QEasingCurve.Type.InCubic))
        if on_end:
            anim.finished.connect(on_end)
        anim.start()
        toast._fade = anim

    def _remove(self, toast: _Toast) -> None:
        if toast in self._active:
            self._active.remove(toast)
        self._layout.removeWidget(toast)
        toast.setParent(None)
        toast.deleteLater()
        self._reposition()

    def _reposition(self) -> None:
        """Restack toasts upward from the bottom-right corner."""
        if not self._parent:
            return
        width = max((t.width() for t in self._active), default=self.MIN_WIDTH)
        height = sum(t.height() for t in self._active)
        height += self._layout.spacing() * max(0, len(self._active) - 1)

        self.setFixedSize(width, max(height, 1))
        self.move(max(24, self._parent.width() - width - 30),
                  max(24, self._parent.height() - height - 54))

        y = self.height()
        for toast in reversed(self._active):
            y -= toast.height()
            toast.move(QPoint(0, max(0, y)))
            toast.show()
            toast.raise_()
            y -= self._layout.spacing()
