"""
Modal overlays and dialogs.

Two kinds live here:

* :class:`OverlayHost` - an **in-window** overlay. This is the key to the
  export UX: it is a child of the main window, so it never calls ``exec()``
  and never blocks the event loop. While an export runs, the sidebar stays
  clickable and the user can jump to any page; the overlay simply follows.
* Real ``QDialog`` subclasses for short, blocking confirmations.

All overlays animate in (fade + pop) and out (fade), and always clean up their
graphics effects so repeated opens cannot stack dead animations.
"""

from __future__ import annotations

import os
from typing import Callable, Dict, List, Optional

from PySide6.QtCore import (
    QEasingCurve, QPropertyAnimation, Qt, QTimer, Signal,
)
from PySide6.QtWidgets import (
    QFrame, QGraphicsOpacityEffect, QGridLayout, QHBoxLayout, QLabel,
    QProgressBar, QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

from .animations import (
    FAST, NORMAL, SLOW, fade_in, fade_out, pop_in, reduced_motion,
)
from .icons import get_svg_icon, get_svg_pixmap
from .theme import ThemeManager, ThemeTokens


class OverlayHost(QWidget):
    """A scrim + card drawn on top of its parent window.

    Unlike ``QDialog.exec()`` this returns immediately, so the rest of the app
    keeps running. That is what lets the user navigate away from the export
    page while reports are still being written.
    """

    closed = Signal()

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self._parent = parent
        self._card: Optional[QWidget] = None
        self._open = False

        self.setObjectName("ModalRoot")
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.hide()

    # -- geometry ----------------------------------------------------------

    def _card_geometry(self, card: QWidget) -> None:
        """Centre ``card`` inside this overlay, clamped to the parent size."""
        pw, ph = self.width(), self.height()
        cw = min(card.sizeHint().width(), max(pw - 80, 320))
        ch = min(card.sizeHint().height(), max(ph - 80, 240))
        card.setGeometry((pw - cw) // 2, (ph - ch) // 2, cw, ch)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if self._card is not None:
            self._card_geometry(self._card)

    # -- show / hide -------------------------------------------------------

    def _present(self, card: QWidget) -> QWidget:
        """Install ``card`` and animate the overlay in."""
        if self._card is not None:
            self._card.setParent(None)
            self._card.deleteLater()
        self._card = card
        self.setGeometry(self._parent.rect())
        self._card_geometry(card)
        self.show()
        self.raise_()
        self._open = True
        if not reduced_motion():
            pop_in(card, SLOW, scale=0.92)
        fade_in(self, FAST, start=0.0)
        return card

    def hide_animated(self) -> None:
        """Fade out, then hide and emit :attr:`closed`."""
        if not self._open:
            return
        self._open = False

        def _cleanup() -> None:
            self.hide()
            if self._card is not None:
                self._card.setParent(None)
                self._card.deleteLater()
                self._card = None
            self.closed.emit()

        if self.graphicsEffect() is None:
            self.setGraphicsEffect(QGraphicsOpacityEffect(self))
        fade_out(self, NORMAL, on_finished=_cleanup)
def _modal_card(title: str, subtitle: str = "", icon_name: str = "info",
                state: str = "") -> tuple[QWidget, dict]:
    """Build the standard modal card shell; returns it plus handles by name."""
    card = QFrame()
    card.setObjectName("ModalCard")
    card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)

    outer = QVBoxLayout(card)
    outer.setContentsMargins(26, 24, 26, 22)
    outer.setSpacing(16)

    head = QHBoxLayout()
    head.setSpacing(14)

    icon_box = QFrame()
    icon_box.setObjectName("ModalIcon")
    icon_box.setProperty("state", state or "info")
    icon_box.setFixedSize(46, 46)
    icon_lay = QVBoxLayout(icon_box)
    icon_lay.setContentsMargins(0, 0, 0, 0)
    icon_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
    icon = QLabel()
    icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
    icon_lay.addWidget(icon)
    head.addWidget(icon_box)

    titles = QVBoxLayout()
    titles.setSpacing(2)
    title_lbl = QLabel(title)
    title_lbl.setObjectName("ModalTitle")
    title_lbl.setWordWrap(True)
    titles.addWidget(title_lbl)
    sub_lbl = QLabel(subtitle)
    sub_lbl.setObjectName("ModalBody")
    sub_lbl.setWordWrap(True)
    sub_lbl.setVisible(bool(subtitle))
    titles.addWidget(sub_lbl)
    head.addLayout(titles, 1)
    outer.addLayout(head)

    return card, {
        "icon": icon, "icon_box": icon_box,
        "title": title_lbl, "subtitle": sub_lbl,
        "body": outer,
    }


def _paint_icon(handles: dict, icon_name: str, state: str = "") -> None:
    """Render an SVG icon into a modal card, coloured by semantic state."""
    t = ThemeManager.current()
    color = {"success": t.success, "error": t.danger,
             "warning": t.warning}.get(state, t.accent)
    handles["icon"].setPixmap(get_svg_pixmap(icon_name, size=24, color=color))
    handles["icon_box"].setProperty("state", state or "info")
    handles["icon_box"].style().unpolish(handles["icon_box"])
    handles["icon_box"].style().polish(handles["icon_box"])


def action_row(*buttons: QPushButton) -> QHBoxLayout:
    """Right-aligned action row with consistent spacing."""
    row = QHBoxLayout()
    row.setSpacing(8)
    row.addStretch(1)
    for btn in buttons:
        row.addWidget(btn)
    return row


class StageRow(QFrame):
    """One progress line in the export overlay: icon, label and detail."""

    def __init__(self, label: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("StageRow")
        self.setProperty("state", "pending")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(13, 10, 13, 10)
        lay.setSpacing(11)

        self.icon = QLabel()
        self.icon.setFixedSize(18, 18)
        self.icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.icon)

        col = QVBoxLayout()
        col.setSpacing(1)
        self.label = QLabel(label)
        self.label.setObjectName("StageLabel")
        self.detail = QLabel("waiting…")
        self.detail.setObjectName("StageDetail")
        self.detail.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)
        col.addWidget(self.label)
        col.addWidget(self.detail)
        lay.addLayout(col, 1)
        self.refresh()

    def set_state(self, state: str, detail: str = "") -> None:
        """state is one of ``pending`` / ``running`` / ``done`` / ``failed``."""
        self.setProperty("state", state)
        self.style().unpolish(self)
        self.style().polish(self)
        icon_name = {
            "pending": "clock", "running": "activity",
            "done": "check-circle", "failed": "alert-circle",
        }.get(state, "clock")
        t = ThemeManager.current()
        color = {
            "pending": t.text_muted, "running": t.accent,
            "done": t.success, "failed": t.danger,
        }.get(state, t.text_muted)
        self.icon.setPixmap(get_svg_pixmap(icon_name, size=18, color=color))
        if detail:
            self.detail.setText(detail)

    def refresh(self) -> None:
        self.set_state(self.property("state") or "pending")
class ExportOverlay(OverlayHost):
    """Animated progress overlay for report generation.

    Design notes:

    * It is an :class:`OverlayHost`, so the rest of the window stays live -
      the user can change pages or start another scan while it runs.
    * Every stage gets its own pending/running/done/failed row, so partial
      failures stay visible instead of collapsing into one message.
    * The success state offers **Open folder**, **Open report** and **Back to
      analysis** - the missing step that used to leave users stranded after an
      export with no obvious way back into the app.
    """

    openRequested = Signal(str)      # filesystem path
    backRequested = Signal()         # "take me back to the analyser"
    beginRequested = Signal()        # user pressed "Try again"

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self._stages: List[StageRow] = []
        self._entries: List[tuple[str, str, str]] = []
        self._busy = False
        self._total = 1
        self._bar: Optional[QProgressBar] = None
        self._pct: Optional[QLabel] = None
        self._status: Optional[QLabel] = None

    @property
    def busy(self) -> bool:
        return self._busy

    # -- lifecycle ---------------------------------------------------------

    def begin(self, title: str, entries: List[tuple[str, str, str]]) -> None:
        """Show the overlay with one row per planned report."""
        self._entries = entries
        self._stages = []
        self._total = max(1, len(entries))

        card, h = _modal_card(
            title,
            "Reports are generated on a background thread - you can keep "
            "browsing the app while this runs.", "export")
        _paint_icon(h, "export")
        lay: QVBoxLayout = h["body"]

        rows = QVBoxLayout()
        rows.setSpacing(7)
        for _key, label, filename in entries:
            stage = StageRow(f"{label}  →  {filename}")
            self._stages.append(stage)
            rows.addWidget(stage)
        lay.addLayout(rows)

        self._pct = QLabel("0%")
        self._pct.setObjectName("ModalMeta")
        self._pct.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(6)

        progress_row = QHBoxLayout()
        progress_row.addWidget(self._bar, 1)
        progress_row.addWidget(self._pct)
        lay.addLayout(progress_row)

        self._status = QLabel("Preparing…")
        self._status.setObjectName("ModalMeta")
        self._status.setWordWrap(True)
        lay.addWidget(self._status)

        cancel_btn = QPushButton("Hide")
        cancel_btn.setObjectName("GhostButton")
        cancel_btn.setToolTip("Keep this running in the background")
        cancel_btn.clicked.connect(self.hide_animated)

        keep_btn = QPushButton("Keep Browsing")
        keep_btn.setObjectName("RunButton")
        keep_btn.setIcon(get_svg_icon("chevron-right", color="#ffffff", size=16))
        keep_btn.clicked.connect(self.hide_animated)
        lay.addLayout(action_row(cancel_btn, keep_btn))

        self._card = self._present(card)
        self._busy = True
        self._set_progress(0)

    # -- progress ----------------------------------------------------------

    def start_stage(self, index: int, note: str = "writing…") -> None:
        """Mark stage ``index`` running; earlier stages settle as done."""
        for i, stage in enumerate(self._stages):
            if i < index:
                if stage.property("state") in (None, "pending", "running"):
                    stage.set_state("done", "done")
            elif i == index:
                stage.set_state("running", note)
            else:
                stage.set_state("pending", "queued")
        self._set_progress(int(index / self._total * 100))

    def finish_stage(self, index: int, detail: str = "done") -> None:
        """Mark stage ``index`` complete with a human-readable ``detail``."""
        if 0 <= index < len(self._stages):
            self._stages[index].set_state("done", detail)
        self._set_progress(int((index + 1) / self._total * 100))

    def fail_stage(self, index: int, detail: str = "failed") -> None:
        """Mark stage ``index`` as failed; remaining stages keep going."""
        if 0 <= index < len(self._stages):
            self._stages[index].set_state("failed", detail)

    def _set_progress(self, pct: int) -> None:
        if self._bar is not None:
            self._bar.setValue(pct)
        if self._pct is not None:
            self._pct.setText(f"{pct}%")

    def set_status(self, text: str) -> None:
        if self._status is not None:
            self._status.setText(text)
# -- completion --------------------------------------------------------

    def complete(self, output_dir: str, written: List[str],
                 failed: int = 0) -> None:
        """Swap the progress UI for the success state and its actions."""
        self._busy = False
        self._set_progress(100)
        ok = failed == 0

        card, h = _modal_card(
            "Export complete" if ok else "Export finished with errors",
            f"{len(written)} report(s) written to the output folder.",
            "check-circle" if ok else "warning",
            "success" if ok else "error")
        _paint_icon(h, "check-circle" if ok else "warning",
                    "success" if ok else "error")
        lay: QVBoxLayout = h["body"]

        listing = QLabel("<br>".join(
            f"•  <b>{os.path.basename(p)}</b>" for p in written)
            or "No files were written.")
        listing.setObjectName("ModalBody")
        listing.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)
        listing.setWordWrap(True)
        lay.addWidget(listing)

        path_lbl = QLabel(output_dir)
        path_lbl.setObjectName("ModalMeta")
        path_lbl.setWordWrap(True)
        path_lbl.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)
        lay.addWidget(path_lbl)

        back_btn = QPushButton("Back to Analysis")
        back_btn.setObjectName("RunButton")
        back_btn.setIcon(get_svg_icon("activity", color="#ffffff", size=16))
        back_btn.setToolTip("Close this dialog and show the Overview page")
        back_btn.clicked.connect(self._on_back)

        open_btn = QPushButton("Open Folder")
        open_btn.setObjectName("GhostButton")
        open_btn.setIcon(get_svg_icon("external", color="#8da2c0", size=16))
        open_btn.clicked.connect(lambda: self.openRequested.emit(output_dir))
        open_btn.setEnabled(os.path.isdir(output_dir))

        done_btn = QPushButton("Close")
        done_btn.setObjectName("GhostButton")
        done_btn.clicked.connect(self.hide_animated)
        lay.addLayout(action_row(open_btn, done_btn, back_btn))
        self._card = self._present(card)

    def fail(self, message: str) -> None:
        """Show a terminal failure state with retry and a way back."""
        self._busy = False
        card, h = _modal_card("Export failed", message, "alert-circle", "error")
        _paint_icon(h, "alert-circle", "error")
        lay: QVBoxLayout = h["body"]

        retry = QPushButton("Try Again")
        retry.setObjectName("RunButton")
        retry.setIcon(get_svg_icon("refresh", color="#ffffff", size=16))
        retry.clicked.connect(self.beginRequested.emit)

        back_btn = QPushButton("Back to Analysis")
        back_btn.setObjectName("GhostButton")
        back_btn.setIcon(get_svg_icon("activity", color="#8da2c0", size=16))
        back_btn.clicked.connect(self._on_back)

        close = QPushButton("Close")
        close.setObjectName("GhostButton")
        close.clicked.connect(self.hide_animated)
        lay.addLayout(action_row(close, back_btn, retry))
        self._card = self._present(card)

    def _on_back(self) -> None:
        """Dismiss the overlay and hand control back to the analysis pages."""
        self.hide_animated()
        self.backRequested.emit()
class ShortcutsOverlay(OverlayHost):
    """Keyboard-shortcut reference, rendered as key caps."""

    SECTIONS = [
        ("Navigation", [
            ("Ctrl + 1…9", "Jump straight to a page"),
            ("Ctrl + O", "Choose a folder to analyze"),
            ("?", "Show this shortcut sheet"),
            ("Esc", "Cancel a running scan / close an overlay"),
        ]),
        ("Analysis", [
            ("F5", "Start or restart a scan"),
            ("Ctrl + R", "Rescan the current folder"),
            ("Ctrl + L", "Focus the folder path field"),
        ]),
        ("Reports", [
            ("Ctrl + E", "Open the Reports page"),
            ("Ctrl + S", "Export the selected formats"),
            ("Ctrl + Shift + O", "Open the last export folder"),
        ]),
        ("Appearance", [
            ("Ctrl + T", "Toggle light / dark theme"),
            ("Ctrl + ,", "Open Settings"),
        ]),
    ]

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)

    def show_sheet(self) -> None:
        """Present the shortcut sheet."""
        card, h = _modal_card(
            "Keyboard shortcuts",
            "Everything you can drive without a mouse.", "keyboard")
        _paint_icon(h, "keyboard")
        lay: QVBoxLayout = h["body"]

        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(7)
        for col, (section, items) in enumerate(self.SECTIONS):
            header = QLabel(section.upper())
            header.setObjectName("SectionTitle")
            grid.addWidget(header, 0, col * 2)
            for row, (key, desc) in enumerate(items, start=1):
                key_lbl = QLabel(key)
                key_lbl.setObjectName("ShortcutKey")
                key_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                grid.addWidget(key_lbl, row, col * 2)
                desc_lbl = QLabel(desc)
                desc_lbl.setObjectName("ShortcutDesc")
                desc_lbl.setWordWrap(True)
                grid.addWidget(desc_lbl, row, col * 2 + 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)
        lay.addLayout(grid)

        close = QPushButton("Got it")
        close.setObjectName("RunButton")
        close.clicked.connect(self.hide_animated)
        lay.addLayout(action_row(close))
        self._card = self._present(card)
class ThemeOverlay(OverlayHost):
    """Live theme/accent picker: click a swatch to apply instantly."""

    themePicked = Signal(str)
    accentPicked = Signal(str)

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self._swatches: Dict[str, QFrame] = {}
        self._accent_swatches: Dict[str, QFrame] = {}

    def show_picker(self, current_theme: str, current_accent: str,
                    themes: Dict[str, object],
                    accents: Dict[str, str]) -> None:
        """Present the picker: one card per theme, one dot per accent."""
        card, h = _modal_card(
            "Appearance", "Pick a theme and an accent - changes apply live.",
            "sparkles")
        _paint_icon(h, "sparkles")
        lay: QVBoxLayout = h["body"]

        theme_head = QLabel("THEME")
        theme_head.setObjectName("SectionTitle")
        lay.addWidget(theme_head)

        grid = QGridLayout()
        grid.setSpacing(8)
        for i, (key, tok) in enumerate(themes.items()):
            swatch = _theme_swatch(tok, key == current_theme)
            swatch.clicked.connect(lambda k=key: self._pick_theme(k))
            self._swatches[key] = swatch
            grid.addWidget(swatch, i // 3, i % 3)
        lay.addLayout(grid)

        accent_head = QLabel("ACCENT")
        accent_head.setObjectName("SectionTitle")
        lay.addWidget(accent_head)

        row = QHBoxLayout()
        row.setSpacing(8)
        for color in accents.values():
            chip = _accent_chip(color, color == current_accent)
            chip.clicked.connect(lambda c=color: self._pick_accent(c))
            self._accent_swatches[color] = chip
            row.addWidget(chip)
        row.addStretch(1)
        lay.addLayout(row)

        close = QPushButton("Done")
        close.setObjectName("RunButton")
        close.clicked.connect(self.hide_animated)
        lay.addLayout(action_row(close))
        self._card = self._present(card)

    def _pick_theme(self, key: str) -> None:
        self.themePicked.emit(key)
        self._mark(self._swatches, key)

    def _pick_accent(self, color: str) -> None:
        self.accentPicked.emit(color)
        self._mark(self._accent_swatches, color)

    @staticmethod
    def _mark(group: Dict[str, QFrame], active: str) -> None:
        for name, widget in group.items():
            widget.setProperty(
                "state", "selected" if name == active else "")
            widget.style().unpolish(widget)
            widget.style().polish(widget)


class ClickableFrame(QFrame):
    """A ``QFrame`` that emits :attr:`clicked` - used by the theme picker."""

    clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


def _theme_swatch(tok: ThemeTokens, selected: bool) -> ClickableFrame:
    """A clickable preview card for one theme."""
    box = ClickableFrame()
    box.setObjectName("Swatch")
    box.setProperty("state", "selected" if selected else "")
    box.setToolTip(f"{tok.name} ({'dark' if tok.dark else 'light'})")

    lay = QVBoxLayout(box)
    lay.setContentsMargins(8, 8, 8, 8)
    lay.setSpacing(6)

    preview = QLabel()
    preview.setFixedHeight(38)
    preview.setStyleSheet(
        f"border-radius: 8px;"
        f"background: qlineargradient(x1:0, y1:0, x2:1, y2:1,"
        f" stop:0 {tok.bg_1}, stop:1 {tok.bg_2});"
        f" border: 1px solid {tok.border_strong};")
    lay.addWidget(preview)

    name = QLabel(tok.name)
    name.setStyleSheet(
        f"color: {tok.text_strong}; font-size: 11px; font-weight: 700;")
    name.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lay.addWidget(name)
    return box


def _accent_chip(color: str, selected: bool) -> ClickableFrame:
    """A clickable colour dot for the accent picker."""
    chip = ClickableFrame()
    chip.setObjectName("Swatch")
    chip.setProperty("state", "selected" if selected else "")
    chip.setFixedSize(30, 30)
    chip.setToolTip(color)
    chip.setStyleSheet(
        f"#Swatch {{ background: {color}; border-radius: 8px; }}"
        f"#Swatch[state='selected'] {{ border: 2px solid #ffffff; }}")
    return chip
class ConfirmOverlay(OverlayHost):
    """Yes/no confirmation rendered in the same visual language as the rest."""

    confirmed = Signal()
    cancelled = Signal()

    def ask(self, title: str, message: str, confirm_text: str = "Confirm",
            danger: bool = False, icon_name: str = "help") -> None:
        """Present the question."""
        card, h = _modal_card(title, message, icon_name,
                              "error" if danger else "info")
        _paint_icon(h, icon_name, "error" if danger else "info")
        lay: QVBoxLayout = h["body"]

        cancel = QPushButton("Cancel")
        cancel.setObjectName("GhostButton")
        cancel.clicked.connect(self._on_cancel)

        confirm = QPushButton(confirm_text)
        confirm.setObjectName("DangerButton" if danger else "RunButton")
        confirm.clicked.connect(self._on_confirm)
        lay.addLayout(action_row(cancel, confirm))
        self._card = self._present(card)

    def _on_confirm(self) -> None:
        self.hide_animated()
        self.confirmed.emit()

    def _on_cancel(self) -> None:
        self.hide_animated()
        self.cancelled.emit()


def open_path(path: str) -> bool:
    """Reveal ``path`` in the OS file manager. Returns True on success."""
    import os
    import subprocess
    import sys

    try:
        if not path or not os.path.exists(path):
            return False
        if sys.platform.startswith("win"):
            os.startfile(path)                  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
        return True
    except OSError:
        return False
