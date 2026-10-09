"""
Reusable, theme-aware UI components.

These replace the ad-hoc widget construction that previously lived inside
``pages.py``. Every widget reads colours from the active
:class:`~ui.theme.ThemeTokens` at construction time and re-reads them when
``ThemeManager.themeChanged`` fires, so a theme switch never leaves stale
colours behind.
"""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QSizePolicy, QVBoxLayout, QWidget,
)

from .animations import count_up, reduced_motion
from .icons import get_category_svg_icon, get_svg_icon, get_svg_pixmap
from .theme import ThemeManager, ThemeTokens


def tokens() -> ThemeTokens:
    """Active theme tokens (falls back to defaults with no app running)."""
    return ThemeManager.current()


# Theme listeners are deliberately drained in small batches.  Scheduling one
# ``singleShot(0, ...)`` per icon/card merely moves all the work into the same
# subsequent event-loop turn, which still feels like a freeze.
_THEME_TASKS: list[Callable[[], None]] = []
_THEME_PUMP_ACTIVE = False
_THEME_TASK_BATCH = 8


def _enqueue_theme_task(task: Callable[[], None]) -> None:
    global _THEME_PUMP_ACTIVE
    _THEME_TASKS.append(task)
    if _THEME_PUMP_ACTIVE:
        return
    _THEME_PUMP_ACTIVE = True
    QTimer.singleShot(0, _drain_theme_tasks)


def _drain_theme_tasks() -> None:
    global _THEME_PUMP_ACTIVE
    for _ in range(min(_THEME_TASK_BATCH, len(_THEME_TASKS))):
        _THEME_TASKS.pop(0)()
    if _THEME_TASKS:
        QTimer.singleShot(16, _drain_theme_tasks)
    else:
        _THEME_PUMP_ACTIVE = False


def _subscribe(widget: QWidget, slot: Callable[[ThemeTokens], None]) -> None:
    """Call ``slot`` now and on every theme change, until ``widget`` dies.

    The change callback is *deferred to the next event-loop turn* rather
    than run inside the signal emission. With dozens of subscribers
    (every StatCard, IconLabel, tool_button, InsightCard, …) that used to
    mean dozens of SVG renders + per-widget setStyleSheet calls executed
    back-to-back on the GUI thread, inside ``themeChanged.emit`` - which
    is exactly what made the theme switch look like a freeze.

    Deferring spreads the per-widget work across event-loop turns, so the
    window stays responsive (and repaints) throughout the fan-out.
    """
    manager = ThemeManager.instance()
    slot(tokens())

    state = {"pending": False}

    def _on_change(_t: ThemeTokens) -> None:
        # Per-widget debounce: if two theme changes fire back-to-back,
        # only the latest survives and the slot runs once.
        if state["pending"]:
            return
        state["pending"] = True

        def _run() -> None:
            state["pending"] = False
            # Widget was destroyed between queueing and running.
            try:
                if widget is None or widget.parent() is None:
                    try:
                        manager.themeChanged.disconnect(_on_change)
                    except (RuntimeError, TypeError):
                        pass
                    return
                slot(manager.tokens)
            except RuntimeError:
                try:
                    manager.themeChanged.disconnect(_on_change)
                except (RuntimeError, TypeError):
                    pass

        _enqueue_theme_task(_run)

    manager.themeChanged.connect(_on_change)


# ---------------------------------------------------------------------------
# Labels & chips
# ---------------------------------------------------------------------------

class Pill(QLabel):
    """Small rounded status chip."""

    def __init__(self, text: str = "", kind: str = "info",
                 parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setProperty("kind", kind)
        self._restyle()

    def set_kind(self, kind: str) -> None:
        self.setProperty("kind", kind)
        self._restyle()

    def _restyle(self) -> None:
        t = tokens()
        color = {
            "info": t.accent, "success": t.success,
            "warning": t.warning, "danger": t.danger,
            "neutral": t.text_muted,
        }.get(self.property("kind"), t.accent)
        self.setStyleSheet(
            f"color: {color}; background: transparent; border: none;"
            f" font-size: 11px; font-weight: 700;")


class IconLabel(QLabel):
    """A pixmap label that re-colours itself on theme change.

    Visibility-aware: rendering an SVG to a pixmap costs ~3-6 ms because
    ``QSvgRenderer`` parses the XML and rasterises it through ``QPainter``,
    and the pixmap cache always misses on a colour change. With 80-150
    icons on the widget tree, a naive refresh on theme change was the
    single largest cost of the switch (0.5-1 s). Hidden pages do not need
    to pay it: they only need to know they owe a refresh, which they do on
    their next ``showEvent``.
    """

    def __init__(self, icon_name: str, size: int = 18,
                 color_role: str = "accent",
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._icon_name = icon_name
        self._size = size
        self._role = color_role
        self._dirty = False
        self.setFixedSize(size + 8, size + 8)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.refresh()

    def set_role(self, color_role: str) -> None:
        self._role = color_role
        self.refresh()

    def refresh(self) -> None:
        """Re-render the icon; skip the work while the label is hidden.

        ``isVisible()`` accounts for the whole ancestor chain, so an icon
        inside a hidden page reports hidden. The pending flag is consumed
        by :meth:`showEvent` when the page is next shown.
        """
        if not self.isVisible():
            self._dirty = True
            return
        self._dirty = False
        t = tokens()
        self.setPixmap(get_svg_pixmap(
            self._icon_name, size=self._size,
            color=getattr(t, self._role, t.accent)))

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        if self._dirty:
            self.refresh()


class SectionHeader(QWidget):
    """Grouped section label: uppercase title, subtitle and optional actions."""

    def __init__(self, title: str, subtitle: str = "",
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        box = QVBoxLayout()
        box.setSpacing(1)
        self.title = QLabel(title.upper())
        self.title.setObjectName("SectionTitle")
        box.addWidget(self.title)
        self.subtitle = QLabel(subtitle)
        self.subtitle.setObjectName("SectionSubtitle")
        self.subtitle.setVisible(bool(subtitle))
        box.addWidget(self.subtitle)
        lay.addLayout(box)
        lay.addStretch(1)

        self.actions = QHBoxLayout()
        self.actions.setSpacing(6)
        lay.addLayout(self.actions)

    def add_action(self, widget: QWidget) -> None:
        self.actions.addWidget(widget)
# ---------------------------------------------------------------------------
# Containers
# ---------------------------------------------------------------------------

class GlassPanel(QFrame):
    """Surface container with an optional header, badge and action row."""

    def __init__(self, title: str = "", icon_name: str = "layers",
                 subtitle: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("GlassPanel")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 16, 18, 16)
        outer.setSpacing(12)

        header = QHBoxLayout()
        header.setSpacing(10)
        self.icon = IconLabel(icon_name, size=18)
        header.addWidget(self.icon)

        box = QVBoxLayout()
        box.setSpacing(1)
        self.title = QLabel(title)
        self.title.setObjectName("PanelTitle")
        self.subtitle = QLabel(subtitle)
        self.subtitle.setObjectName("PanelSubtitle")
        self.subtitle.setVisible(bool(subtitle))
        box.addWidget(self.title)
        box.addWidget(self.subtitle)
        header.addLayout(box)
        header.addStretch(1)

        self.header_actions = QHBoxLayout()
        self.header_actions.setSpacing(6)
        header.addLayout(self.header_actions)
        outer.addLayout(header)

        self.body = QVBoxLayout()
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.setSpacing(10)
        outer.addLayout(self.body, 1)

    def add_header_widget(self, widget: QWidget) -> None:
        self.header_actions.addWidget(widget)

    def set_badge(self, text: str) -> QLabel:
        badge = QLabel(text)
        badge.setObjectName("PanelBadge")
        self.add_header_widget(badge)
        return badge

    def add(self, widget: QWidget, stretch: int = 0) -> QWidget:
        self.body.addWidget(widget, stretch)
        return widget
class StatCard(QFrame):
    """KPI card: icon, label, animated value, subtitle and optional trend."""

    def __init__(self, title: str, value: str = "—", subtitle: str = "",
                 icon_name: str = "activity", accent: str = "blue",
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("StatCard")
        self.setProperty("accent", accent)
        self._accent_role = {
            "cyan": "info", "blue": "accent", "violet": "accent_2",
            "green": "success", "amber": "warning", "red": "danger",
        }.get(accent, "accent")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 14, 18, 14)
        outer.setSpacing(6)

        top = QHBoxLayout()
        top.setSpacing(10)
        self.icon = IconLabel(icon_name, size=18, color_role=self._accent_role)
        top.addWidget(self.icon)

        self.title = QLabel(title.upper())
        self.title.setObjectName("StatCardTitle")
        top.addWidget(self.title)
        top.addStretch(1)

        self.trend = QLabel("")
        self.trend.setObjectName("StatCardTrend")
        self.trend.setVisible(False)
        top.addWidget(self.trend)
        outer.addLayout(top)

        self.value = QLabel(value)
        self.value.setObjectName("StatCardValue")
        self.value.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)
        outer.addWidget(self.value)

        self.subtitle = QLabel(subtitle)
        self.subtitle.setObjectName("StatCardSub")
        self.subtitle.setWordWrap(True)
        outer.addWidget(self.subtitle)
        outer.addStretch(1)

        _subscribe(self, self._on_theme)

    def _on_theme(self, t: ThemeTokens) -> None:
        color = getattr(t, self._accent_role, t.accent)
        # IconLabel.refresh() is a no-op work-wise when hidden; only the
        # inline stylesheet below is cheap enough to always set.
        self.icon.refresh()
        self.icon.setStyleSheet(f"background: {color}22; border-radius: 9px;")

    def set_value(self, value: str, subtitle: Optional[str] = None,
                  trend: Optional[str] = None, animate: bool = True) -> None:
        """Update the card; the number counts up when ``animate`` is set."""
        if animate and not reduced_motion():
            count_up(self.value, value)
        else:
            self.value.setText(value)
        if subtitle is not None:
            self.subtitle.setText(subtitle)
        if trend is None:
            self.trend.setVisible(False)
            return
        self.trend.setText(trend)
        self.trend.setVisible(True)
        stripped = trend.strip()
        kind = ("up" if stripped.startswith("↑")
                else "down" if stripped.startswith("↓") else "flat")
        self.trend.setProperty("trend", kind)
        self.trend.style().unpolish(self.trend)
        self.trend.style().polish(self.trend)
class InsightCard(QFrame):
    """Severity-coded message row used for insights and recommendations."""

    def __init__(self, severity: str, icon_name: str, text: str,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("InsightCard")
        self.setProperty("severity", severity)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 9, 12, 9)
        lay.setSpacing(10)

        role = {"critical": "danger", "warning": "warning",
                "success": "success"}.get(severity, "accent")
        icon = IconLabel(icon_name, size=16, color_role=role)
        lay.addWidget(icon, 0, Qt.AlignmentFlag.AlignTop)

        self.text = QLabel(text)
        self.text.setWordWrap(True)
        self._restyle_text()
        lay.addWidget(self.text, 1)

    def _restyle_text(self) -> None:
        t = tokens()
        self.text.setStyleSheet(
            f"color: {t.text}; font-size: 13px; font-weight: 500;")

    def set_text(self, text: str) -> None:
        self._restyle_text()
        self.text.setText(text)


class EmptyState(QWidget):
    """Friendly placeholder for pages and tables with no data yet."""

    def __init__(self, title: str, body: str = "", icon_name: str = "search",
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 36, 24, 36)
        lay.setSpacing(8)
        lay.addStretch(1)

        self.icon = IconLabel(icon_name, size=32, color_role="text_faint")
        self.icon.setFixedSize(44, 44)
        lay.addWidget(self.icon, 0, Qt.AlignmentFlag.AlignHCenter)

        self.title = QLabel(title)
        self.title.setObjectName("EmptyStateTitle")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.title)

        self.body = QLabel(body)
        self.body.setObjectName("EmptyStateBody")
        self.body.setWordWrap(True)
        self.body.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.body.setVisible(bool(body))
        lay.addWidget(self.body)
        lay.addStretch(1)
# ---------------------------------------------------------------------------
# Buttons & controls
# ---------------------------------------------------------------------------

def tool_button(icon_name: str, tooltip: str, on_click: Callable[[], None],
                checkable: bool = False, role: str = "text_dim",
                size: int = 32) -> QPushButton:
    """Compact icon-only button that follows the theme colours.

    Uses the same visibility-aware refresh as :class:`IconLabel` so icons
    inside hidden overlays or off-screen top-levels do not incur an SVG
    re-render on every theme change.
    """
    from PySide6.QtCore import QSize

    class _ToolButton(QPushButton):
        _dirty_icon = False

        def showEvent(self, event) -> None:  # noqa: N802
            super().showEvent(event)
            if self._dirty_icon:
                self._dirty_icon = False
                apply_icon(ThemeManager.current())

    btn = _ToolButton()
    btn.setObjectName("IconButton")
    btn.setCheckable(checkable)
    btn.setToolTip(tooltip)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setFixedSize(size, size)
    btn.setIconSize(QSize(size - 16, size - 16))
    btn.clicked.connect(on_click)

    def apply_icon(t: ThemeTokens) -> None:
        if not btn.isVisible():
            btn._dirty_icon = True
            return
        btn.setIcon(get_svg_icon(
            icon_name, color=getattr(t, role, t.text_dim),
            active_color=t.text_strong, size=size - 16))

    _subscribe(btn, apply_icon)
    return btn


class SegmentedControl(QWidget):
    """Radio-style button group (used for view modes and export presets)."""

    changed = Signal(str)

    def __init__(self, options: list[str], value: str = "",
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._buttons: dict[str, QPushButton] = {}

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)

        for name in options:
            btn = QPushButton(name)
            btn.setObjectName("SegmentButton")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _=False, n=name: self.set_value(n))
            self._buttons[name] = btn
            lay.addWidget(btn)
        lay.addStretch(1)
        self.set_value(value or (options[0] if options else ""))

    def set_value(self, value: str) -> None:
        """Select ``value`` without re-emitting when unchanged."""
        if value not in self._buttons:
            return
        already = self._buttons[value].isChecked()
        for name, btn in self._buttons.items():
            btn.setChecked(name == value)
        if not already:
            self.changed.emit(value)

    def value(self) -> str:
        for name, btn in self._buttons.items():
            if btn.isChecked():
                return name
        return ""

    def set_enabled(self, enabled: bool) -> None:
        for btn in self._buttons.values():
            btn.setEnabled(enabled)


class CheckCard(QFrame):
    """Selectable option card with a checkbox, icon, title and description."""

    toggled = Signal(bool)

    def __init__(self, title: str, description: str, icon_name: str,
                 checked: bool = True, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("InsightCard")
        self.setProperty("severity", "info")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(13, 11, 13, 11)
        lay.setSpacing(12)

        self.icon = IconLabel(icon_name, size=20, color_role="accent")
        lay.addWidget(self.icon, 0, Qt.AlignmentFlag.AlignTop)

        col = QVBoxLayout()
        col.setSpacing(2)
        t = tokens()
        self.title = QLabel(title)
        self.title.setStyleSheet(
            f"color: {t.text_strong}; font-size: 13px; font-weight: 700;")
        self.description = QLabel(description)
        self.description.setWordWrap(True)
        self.description.setStyleSheet(
            f"color: {t.text_dim}; font-size: 11px;")
        col.addWidget(self.title)
        col.addWidget(self.description)
        lay.addLayout(col, 1)

        self.check = QCheckBox()
        self.check.setChecked(checked)
        self.check.toggled.connect(self.toggled.emit)
        lay.addWidget(self.check, 0, Qt.AlignmentFlag.AlignTop)

    def is_checked(self) -> bool:
        return self.check.isChecked()

    def set_checked(self, value: bool) -> None:
        self.check.setChecked(value)


class FilterBar(QWidget):
    """Search box bound to a table plus a live visible-row counter."""

    def __init__(self, table, placeholder: str = "Filter rows…",
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._table = table

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        self.search_icon = IconLabel("search", size=14, color_role="text_faint")
        lay.addWidget(self.search_icon)

        self.input = QLineEdit()
        self.input.setPlaceholderText(placeholder)
        self.input.setClearButtonEnabled(True)
        self.input.textChanged.connect(self._apply)
        lay.addWidget(self.input, 1)

        self.count = QLabel("")
        self.count.setObjectName("PanelSubtitle")
        lay.addWidget(self.count)
        self._apply("")

    def _apply(self, text: str) -> None:
        needle = text.lower().strip()
        visible = 0
        for r in range(self._table.rowCount()):
            match = False
            for c in range(self._table.columnCount()):
                item = self._table.item(r, c)
                if item is not None and needle in item.text().lower():
                    match = True
                    break
            self._table.setRowHidden(r, not match)
            visible += int(match)
        total = self._table.rowCount()
        self.count.setText(f"{visible}/{total}" if needle else f"{total} rows")
# ---------------------------------------------------------------------------
# Data views
# ---------------------------------------------------------------------------

def make_table(headers: list[str], stretch_column: int = 0) -> QTableWidget:
    """Configured, sortable, non-editable table used across all pages."""
    from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QTableWidget

    table = QTableWidget(0, len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.verticalHeader().setVisible(False)
    table.setAlternatingRowColors(True)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.setWordWrap(False)
    table.setShowGrid(False)
    table.setSortingEnabled(True)
    table.horizontalHeader().setHighlightSections(False)
    table.horizontalHeader().setSectionResizeMode(
        QHeaderView.ResizeMode.Interactive)
    table.horizontalHeader().setStretchLastSection(True)
    if stretch_column < len(headers):
        table.horizontalHeader().setSectionResizeMode(
            stretch_column, QHeaderView.ResizeMode.Stretch)
    return table


def fill_table(table, rows: list[list]) -> None:
    """Replace a table's contents, right-aligning numeric-looking cells."""
    from PySide6.QtWidgets import QTableWidgetItem

    table.setSortingEnabled(False)
    table.setRowCount(0)
    for row in rows:
        idx = table.rowCount()
        table.insertRow(idx)
        for col, value in enumerate(row):
            item = (value if isinstance(value, QTableWidgetItem)
                    else QTableWidgetItem(str(value)))
            if not isinstance(value, QTableWidgetItem) and col > 0:
                if any(ch.isdigit() for ch in str(value)):
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            table.setItem(idx, col, item)
    if table.rowCount():
        table.resizeColumnsToContents()
        table.setColumnWidth(0, max(table.columnWidth(0), 200))
    table.setSortingEnabled(True)


def file_row(record: dict, columns: tuple[str, ...] = ()) -> list:
    """Build a table row from an analyzer record, with a category icon.

    ``Qt.UserRole`` on the first cell carries the absolute path, which is what
    the viewer's double-click handler reads.
    """
    from PySide6.QtWidgets import QTableWidgetItem

    cols = columns or ("name", "parent", "type", "size_formatted",
                       "modified_formatted")
    name_item = QTableWidgetItem(
        get_category_svg_icon(record.get("type", "Other"), size=16),
        "  " + str(record.get("name", "")))
    path = record.get("path", "")
    if path:
        name_item.setData(Qt.ItemDataRole.UserRole, path)
    values = {
        "name": name_item,
        "parent": str(record.get("parent", "")),
        "type": str(record.get("type", "")),
        "size_formatted": str(record.get("size_formatted", "")),
        "modified_formatted": str(record.get("modified_formatted", "")),
        "depth": str(record.get("depth", "")),
        "path_len": str(record.get("path_len", "")),
        "age_days": f"{record.get('age_days', 0):,}",
    }
    return [values.get(col, str(record.get(col, ""))) for col in cols]


def section_rows(rows: list[dict], columns: tuple[str, ...]) -> list[list]:
    """Generic record -> row mapping for non-file breakdowns."""
    return [[str(row.get(col, "")) for col in columns] for row in rows]
