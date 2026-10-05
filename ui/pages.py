"""
Page widgets for the main window.

Every page is built from the shared kit in :mod:`ui.widgets` and inherits from
:class:`Page`, which supplies the standard contract:

* ``set_result(result)`` - push an :class:`AnalysisResult` into the view
* ``set_empty()``        - return to the "no data yet" presentation
* ``on_theme_changed()`` - re-render anything QSS cannot express (charts)

Two pages are new relative to the previous layout: :class:`ReportsPage`
(the unified export frame) and :class:`SettingsPage`.
"""

from __future__ import annotations

import os
from typing import Any, Callable, Dict, List, Optional

from PySide6.QtCore import QEasingCurve, QSize, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QFileDialog, QFrame, QGridLayout,
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea, QSizePolicy,
    QSplitter, QTabWidget, QTableWidgetItem, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QWidget,
)

from folder_analyzer import __version__
from folder_analyzer.formats import format_size
from folder_analyzer.models import AnalysisConfig, AnalysisResult

from .animations import make_scroll, reduced_motion, stagger_in
from .icons import get_category_svg_icon, get_svg_icon, get_svg_pixmap
from .theme import ACCENTS, DENSITIES, THEMES, ThemeManager, ThemeTokens
from .widgets import (
    CheckCard, EmptyState, FilterBar, GlassPanel, InsightCard, Pill,
    SectionHeader, SegmentedControl, StatCard, fill_table, file_row, make_table,
    section_rows, tokens,
)


# ===========================================================================
# Page base class
# ===========================================================================

class Page(QWidget):
    """Common base: stores the last result and reacts to theme changes."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("PageRoot")
        self._result: Optional[AnalysisResult] = None

    # -- contract ----------------------------------------------------------

    def set_result(self, result: AnalysisResult) -> None:  # pragma: no cover
        """Render an analysis result. Subclasses override."""

    def set_empty(self) -> None:  # pragma: no cover
        """Reset to the pre-scan presentation. Subclasses override."""

    # -- helpers -----------------------------------------------------------

    def scroll_body(self) -> tuple[QScrollArea, QVBoxLayout]:
        """Return ``(scroll, inner_layout)`` for a scrollable page body."""
        inner = QWidget()
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(14)
        scroll = make_scroll(inner)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
        return scroll, lay

    @staticmethod
    def card_row(*cards: StatCard) -> QHBoxLayout:
        """Evenly spaced KPI row."""
        row = QHBoxLayout()
        row.setSpacing(12)
        for card in cards:
            row.addWidget(card, 1)
        return row

    @staticmethod
    def card_grid(cards: List[StatCard], columns: int = 4) -> QGridLayout:
        """KPI cards laid out in a fixed-column grid."""
        grid = QGridLayout()
        grid.setSpacing(12)
        for i, card in enumerate(cards):
            grid.addWidget(card, i // columns, i % columns)
        for col in range(columns):
            grid.setColumnStretch(col, 1)
        return grid


def _wire_open_in_viewer(table, callback: Optional[Callable[[str], None]]) -> None:
    """Double-click a row to send its ``UserRole`` path to the file viewer."""
    if callback is None:
        return

    def on_double_click(item) -> None:
        first = table.item(item.row(), 0)
        if first is None:
            return
        path = first.data(Qt.ItemDataRole.UserRole)
        if path:
            callback(str(path))

    table.itemDoubleClicked.connect(on_double_click)
# ===========================================================================
# Chart helpers (theme-aware)
# ===========================================================================

def _series_color(t: ThemeTokens, index: int) -> str:
    palette = t.series or ("#4f8cff", "#8b5cf6", "#06b6d4", "#22c55e",
                           "#f59e0b", "#f43f5e")
    return palette[index % len(palette)]


def _style_chart(chart, t: ThemeTokens) -> None:
    """Apply theme colours to a QChart (QSS cannot reach inside QtCharts)."""
    from PySide6.QtGui import QColor

    chart.setBackgroundVisible(False)
    legend = chart.legend()
    legend.setLabelColor(QColor(t.text_dim))
    legend.setFont(legend.font())
    for axis in chart.axes():
        axis.setLabelsColor(QColor(t.text_dim))
        grid = getattr(axis, "gridLineColor", None)
        if grid is not None and hasattr(axis, "setGridLineColor"):
            axis.setGridLineColor(QColor(_hex_to_rgba(t.text_muted, 0.22)))


def _hex_to_rgba(color: str, alpha: float) -> str:
    c = color.strip()
    if c.startswith(("rgba", "rgb")):
        parts = c[c.index("(") + 1:c.index(")")].split(",")
        r, g, b = (int(float(parts[i])) for i in (0, 1, 2))
        return f"rgba({r},{g},{b},{alpha:.3f})"
    h = c.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha:.3f})"


def _donut(entries: list[dict], value_key: str = "size",
           label_key: str = "label", max_slices: int = 8):
    """Hollow donut chart with a centre hole and a themed legend."""
    from PySide6.QtCharts import QChart, QPieSeries
    from PySide6.QtCore import QMargins
    from PySide6.QtGui import QColor

    t = tokens()
    rows = list(entries[:max_slices])
    if len(entries) > max_slices:
        rest = sum(d.get(value_key, 0) for d in entries[max_slices:])
        rows.append({label_key: "Other", value_key: rest,
                     "color": t.text_muted})
    total = sum(d.get(value_key, 0) for d in rows) or 1

    series = QPieSeries()
    series.setPieSize(0.78)
    series.setHoleSize(0.52)
    for d in rows:
        value = float(d.get(value_key, 0))
        slice_ = series.append(str(d.get(label_key, "?")), value)
        slice_.setBrush(QColor(d.get("color") or _series_color(t, 0)))
        slice_.setLabelVisible(total > 0 and value / total >= 0.06)
        slice_.setLabelColor(QColor(t.text))
        slice_.setBorderColor(QColor(_hex_to_rgba(t.bg_3, 0.9)))

    chart = QChart()
    chart.setTheme(QChart.ChartTheme.ChartThemeDark)
    chart.setAnimationOptions(QChart.AnimationOption.AllAnimations)
    chart.setAnimationDuration(700)
    chart.setAnimationEasingCurve(QEasingCurve(QEasingCurve.Type.OutCubic))
    chart.addSeries(series)
    chart.legend().setVisible(True)
    chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)
    chart.setMargins(QMargins(6, 6, 6, 6))
    _style_chart(chart, t)
    return chart


def _bars(entries: list[dict], value_key: str = "size", label_key: str = "name",
          color: str = ""):
    """Vertical bar chart with a themed value axis."""
    from PySide6.QtCharts import (
        QBarCategoryAxis, QBarSeries, QBarSet, QChart, QValueAxis,
    )
    from PySide6.QtGui import QColor

    t = tokens()
    labels = [str(d.get(label_key, "?")) for d in entries]
    values = [float(d.get(value_key, 0)) for d in entries]

    bar_set = QBarSet("")
    bar_set.setColor(QColor(color or _series_color(t, 0)))
    bar_set.append(values or [0.0])

    series = QBarSeries()
    series.append(bar_set)
    series.setBarWidth(0.55)

    axis_x = QBarCategoryAxis()
    axis_x.append(labels or ["â€”"])
    axis_x.setLabelsColor(QColor(t.text_dim))
    axis_x.setGridLineVisible(False)

    axis_y = QValueAxis()
    axis_y.setLabelFormat("%.0f")
    axis_y.setLabelsColor(QColor(t.text_dim))
    axis_y.setGridLineColor(QColor(_hex_to_rgba(t.text_muted, 0.20)))
    peak = max(values) if values else 1.0
    axis_y.setRange(0, peak * 1.15 if peak else 1)

    chart = QChart()
    chart.setTheme(QChart.ChartTheme.ChartThemeDark)
    chart.setAnimationOptions(QChart.AnimationOption.AllAnimations)
    chart.setAnimationDuration(700)
    chart.setAnimationEasingCurve(QEasingCurve(QEasingCurve.Type.OutCubic))
    chart.addSeries(series)
    chart.setAxisX(axis_x, series)
    chart.setAxisY(axis_y, series)
    chart.legend().setVisible(False)
    _style_chart(chart, t)
    return chart


class ChartView(QWidget):
    """Themed chart container that rebuilds its chart on demand."""

    def __init__(self, builder: Callable[[], Any],
                 min_height: int = 240,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        from PySide6.QtCharts import QChartView
        from PySide6.QtGui import QPainter

        self._builder = builder
        self._view = QChartView()
        self._view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._view.setMinimumHeight(min_height)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._view)

        self._empty = EmptyState("No data yet", "Run a scan to populate this chart.",
                                 "charts")
        lay.addWidget(self._empty)
        self._refresh()

    def rebuild(self) -> None:
        """Re-create the chart so it picks up current theme colours."""
        self._refresh()

    def _refresh(self) -> None:
        chart = None
        try:
            chart = self._builder()
        except Exception:                    # noqa: BLE001 - never crash the UI
            chart = None
        has_data = chart is not None and bool(chart.series())
        self._view.setVisible(has_data)
        self._empty.setVisible(not has_data)
        if has_data:
            self._view.setChart(chart)
# ===========================================================================
# Overview
# ===========================================================================

class OverviewPage(Page):
    """Headline metrics, the top recommendation and the type breakdown."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        _scroll, root = self.scroll_body()

        self.cards = {
            "files": StatCard("Files Indexed", "â€”", "0-byte: â€”", "files", "blue"),
            "dirs": StatCard("Directories", "â€”", "branches scanned",
                             "folder", "violet"),
            "size": StatCard("Total Storage", "â€”", "disk footprint",
                             "hard-drive", "cyan"),
            "avg": StatCard("Average File", "â€”", "mean size", "charts", "violet"),
            "health": StatCard("Health Score", "â€”", "storage efficiency",
                               "health", "green"),
            "dupes": StatCard("Duplicate Waste", "â€”", "recoverable",
                              "duplicates", "red"),
        }
        self._card_order = ("files", "dirs", "size", "avg", "health", "dupes")
        root.addLayout(self.card_grid(
            [self.cards[k] for k in self._card_order], columns=3))

        self.headline = GlassPanel("Recommended Action", "sparkles",
                                   "Highest-impact fix for this folder")
        self.headline_text = QLabel(
            "Run an analysis on any folder to see storage recovery tips.")
        self.headline_text.setWordWrap(True)
        self.headline_text.setStyleSheet(
            f"color: {tokens().text}; font-size: 13px; font-weight: 500;")
        icon_row = QHBoxLayout()
        icon_row.setSpacing(12)
        icon_row.addWidget(self.headline.icon, 0, Qt.AlignmentFlag.AlignTop)
        icon_row.addWidget(self.headline_text, 1)
        self.headline.body.addLayout(icon_row)
        root.addWidget(self.headline)

        panel = GlassPanel("Storage Distribution by File Extension", "files",
                           "Ranked by aggregate size")
        self.type_badge = panel.set_badge("â€” extensions")
        self.type_table = make_table(
            ["Extension", "Category", "Files", "Size", "% of storage"])
        panel.add(FilterBar(self.type_table, "Filter extensionsâ€¦"))
        panel.add(self.type_table, 1)
        root.addWidget(panel, 1)

    def set_empty(self) -> None:
        for key in self._card_order:
            self.cards[key].set_value("â€”", animate=False)
        fill_table(self.type_table, [])
        self.type_badge.setText("â€” extensions")
        self.headline_text.setText(
            "Run an analysis on any folder to see storage recovery tips.")

    def set_result(self, result: AnalysisResult) -> None:
        if not result.has_data:
            self.set_empty()
            return

        self.cards["files"].set_value(
            f"{result.total_files:,}",
            f"{result.empty_files_count:,} zero-byte file(s)")
        self.cards["dirs"].set_value(f"{result.total_directories:,}")
        self.cards["size"].set_value(result.total_storage_formatted)
        self.cards["avg"].set_value(result.avg_file_size_formatted)

        score = result.storage_efficiency_score
        trend = ("â†‘ Healthy" if score >= 80
                 else "â€¢ Fair" if score >= 60 else "â†“ Needs attention")
        self.cards["health"].set_value(f"{score}/100",
                                       result.storage_health_label, trend)
        self.cards["dupes"].set_value(
            result.duplicate_wasted_formatted if result.duplicate_groups else "0 B",
            f"{len(result.duplicate_groups)} duplicate cluster(s)")

        recs = result.actionable_recommendations
        if recs:
            top = recs[0]
            self.headline_text.setText(
                f"<b>{top['title']}</b><br/>{top['action']}")
        else:
            self.headline_text.setText(
                "<b>Optimal layout.</b> Directory storage is well organized "
                "with no detected duplicate waste.")

        rows = []
        for entry in result.file_types:
            item = QTableWidgetItem(
                get_category_svg_icon(entry["category"], size=16),
                "  " + entry["label"])
            rows.append([item, entry["category"], f"{entry['files']:,}",
                         entry["size_formatted"], f"{entry['percentage']}%"])
        fill_table(self.type_table, rows)
        self.type_badge.setText(f"{len(result.file_types)} extensions")
# ===========================================================================
# Charts
# ===========================================================================

class ChartsPage(Page):
    """Six charts over the same result set, all theme-aware."""

    #: (key, panel title, panel icon, subtitle, value_key, label_key, kind)
    CHARTS = [
        ("type", "Storage by File Type", "files", "Top 8 extensions",
         "size", "label", "donut8"),
        ("cat", "Storage by Category", "layers", "Grouped by media class",
         "size", "name", "donut9"),
        ("dirs", "Top Directories", "folder", "Largest aggregate footprint",
         "size", "name", "bars"),
        ("age", "File Age Distribution", "clock", "Recency buckets",
         "size", "category", "bars"),
        ("size_dist", "File Size Distribution", "activity", "Size classes",
         "count", "range", "bars"),
        ("depth", "Depth Distribution", "layers", "Files per nesting level",
         "files", "depth", "bars"),
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        _scroll, root = self.scroll_body()
        self._views: Dict[str, ChartView] = {}

        grid = QGridLayout()
        grid.setSpacing(14)
        for i, (key, title, icon, subtitle, *_rest) in enumerate(self.CHARTS):
            panel = GlassPanel(title, icon, subtitle)
            view = ChartView(lambda k=key: self._build(k))
            self._views[key] = view
            panel.add(view)
            # rows: 0 -> two side-by-side, 1 -> one wide, 2+ -> pairs
            if i < 2:
                grid.addWidget(panel, 0, i)
            elif i == 2:
                grid.addWidget(panel, 1, 0, 1, 2)
            else:
                n = i - 3
                grid.addWidget(panel, 2 + n // 2, n % 2)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setRowStretch(1, 2)
        root.addLayout(grid)

    def _build(self, key: str):
        """Build the chart for ``key`` from the current result."""
        spec = next(c for c in self.CHARTS if c[0] == key)
        _k, _title, _icon, _sub, value_key, label_key, kind = spec
        r = self._result
        if r is None or not r.has_data:
            return None
        if kind.startswith("donut"):
            return _donut(getattr(r, {"donut8": "file_types",
                                      "donut9": "categories"}[kind]),
                          value_key, label_key,
                          8 if kind == "donut8" else 9)
        source = {"dirs": r.top_directories[:10],
                  "age": r.age_distribution,
                  "size_dist": r.size_distribution,
                  "depth": r.depth_distribution}[key]
        return _bars(source, value_key, label_key)

    def set_empty(self) -> None:
        for view in self._views.values():
            view.rebuild()

    def set_result(self, result: AnalysisResult) -> None:
        self._result = result
        for view in self._views.values():
            view.rebuild()
# ===========================================================================
# File explorer
# ===========================================================================

class FilesPage(Page):
    """Largest / oldest / recent / zero-byte file tables."""

    TABS = (("Largest", "largest_files"),
            ("Oldest", "oldest_files"),
            ("Recent", "recent_files"),
            ("0-Byte", "empty_files_list"))

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._viewer_callback: Optional[Callable[[str], None]] = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        panel = GlassPanel("File Explorer", "files",
                           "Double-click a row to preview it in the File Viewer")
        self.file_badge = panel.set_badge("0 files")

        self.tabs = QTabWidget()
        self.tables: Dict[str, Any] = {}
        for name, attr in self.TABS:
            table = make_table(["Name", "Location", "Type", "Size", "Modified"])
            self.tables[name] = table

            wrap = QWidget()
            wrap_lay = QVBoxLayout(wrap)
            wrap_lay.setContentsMargins(0, 6, 0, 0)
            wrap_lay.setSpacing(8)
            wrap_lay.addWidget(FilterBar(table, f"Filter {name.lower()} filesâ€¦"))
            wrap_lay.addWidget(table, 1)
            self.tabs.addTab(wrap, name)
            _wire_open_in_viewer(table, self._on_open_viewer)
            setattr(self, f"table_{attr}", table)

        panel.add(self.tabs, 1)
        root.addWidget(panel, 1)

    def set_viewer_callback(self, cb: Callable[[str], None]) -> None:
        """Register the callback used to open a file in the viewer."""
        self._viewer_callback = cb

    def _on_open_viewer(self, path: str) -> None:
        if self._viewer_callback:
            self._viewer_callback(path)

    def set_empty(self) -> None:
        for table in self.tables.values():
            fill_table(table, [])
        self.file_badge.setText("0 files")

    def set_result(self, result: AnalysisResult) -> None:
        if not result.has_data:
            self.set_empty()
            return
        for table in self.tables.values():
            fill_table(table, [])
        fill_table(self.tables["Largest"],
                   [file_row(r) for r in result.largest_files])
        fill_table(self.tables["Oldest"],
                   [file_row(r) for r in result.oldest_files])
        fill_table(self.tables["Recent"],
                   [file_row(r) for r in getattr(result, "recent_files", [])])
        fill_table(self.tables["0-Byte"],
                   [file_row(r) for r in result.empty_files_list])
        total = sum(len(rows) for rows in (
            result.largest_files, result.oldest_files,
            getattr(result, "recent_files", []), result.empty_files_list))
        self.file_badge.setText(f"{total:,} rows")
# ===========================================================================
# File viewer
# ===========================================================================

class FileViewerPage(Page):
    """Split view: a searchable file tree on the left, preview on the right."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        panel = GlassPanel("File Viewer", "search",
                           "Browse scanned files and preview them in-app")
        self.viewer_badge = panel.set_badge("no scan")

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        left = QWidget()
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(0, 0, 0, 0)
        left_lay.setSpacing(8)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Filter files by nameâ€¦")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._apply_filter)
        left_lay.addWidget(self.search)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["File", "Size"])
        self.tree.setColumnWidth(0, 240)
        self.tree.setAlternatingRowColors(True)
        self.tree.setUniformRowHeights(True)
        self.tree.itemSelectionChanged.connect(self._on_tree_selection)
        left_lay.addWidget(self.tree, 1)
        splitter.addWidget(left)

        from .file_viewer import FileViewer
        self.viewer = FileViewer()
        splitter.addWidget(self.viewer)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([320, 900])
        panel.add(splitter, 1)
        root.addWidget(panel, 1)

    def open_path(self, path: str) -> None:
        """Load ``path`` in the preview pane and select it in the tree."""
        self.viewer.load_file(path)
        self._select_path_in_tree(path)

    def set_empty(self) -> None:
        self.tree.clear()
        self.viewer.clear()
        self.viewer_badge.setText("no scan")

    def set_result(self, result: AnalysisResult) -> None:
        self._result = result
        self.tree.clear()
        if not result.has_data:
            self.viewer_badge.setText("no scan")
            return
        self._rebuild_tree(result)
        self.viewer_badge.setText(f"{result.total_files:,} files")

    def _rebuild_tree(self, result: AnalysisResult) -> None:
        root_item = QTreeWidgetItem([result.root_name + "/", ""])
        root_item.setIcon(0, get_svg_icon("folder", color="#93c5fd", size=16))
        self.tree.addTopLevelItem(root_item)

        by_parent: Dict[str, List[dict]] = {}
        records = (result.largest_files + result.oldest_files
                   + getattr(result, "recent_files", []) + result.empty_files_list)
        for record in records:
            parent = record.get("parent_full") or record.get("path", "")
            by_parent.setdefault(parent, []).append(record)

        for parent_path, recs in sorted(by_parent.items()):
            if not parent_path:
                continue
            try:
                short = os.path.relpath(parent_path, result.root_path)
            except ValueError:
                short = parent_path
            dir_item = QTreeWidgetItem([short, ""])
            dir_item.setIcon(0, get_svg_icon("folder", color="#c4b5fd", size=16))
            root_item.addChild(dir_item)
            for record in recs:
                item = QTreeWidgetItem(
                    [record.get("name", "?"), record.get("size_formatted", "")])
                item.setIcon(0, get_category_svg_icon(
                    record.get("type", "Other"), size=14))
                item.setData(0, Qt.ItemDataRole.UserRole, record.get("path", ""))
                dir_item.addChild(item)
        root_item.setExpanded(True)

    def _apply_filter(self, text: str) -> None:
        needle = text.lower().strip()

        def visit(item: QTreeWidgetItem) -> bool:
            match = needle in item.text(0).lower() if needle else True
            child_match = any(visit(item.child(i))
                              for i in range(item.childCount()))
            show = match or child_match
            item.setHidden(not show)
            if needle and child_match:
                item.setExpanded(True)
            return show

        for i in range(self.tree.topLevelItemCount()):
            visit(self.tree.topLevelItem(i))

    def _on_tree_selection(self) -> None:
        items = self.tree.selectedItems()
        if not items:
            return
        path = items[0].data(0, Qt.ItemDataRole.UserRole)
        if path:
            self.viewer.load_file(str(path))

    def _select_path_in_tree(self, path: str) -> None:
        for i in range(self.tree.topLevelItemCount()):
            found = self._find_child_by_path(self.tree.topLevelItem(i), path)
            if found is not None:
                self.tree.setCurrentItem(found)
                self.tree.scrollToItem(found)
                return

    def _find_child_by_path(self, item: QTreeWidgetItem,
                            path: str) -> Optional[QTreeWidgetItem]:
        if item.data(0, Qt.ItemDataRole.UserRole) == path:
            return item
        for i in range(item.childCount()):
            found = self._find_child_by_path(item.child(i), path)
            if found is not None:
                item.setExpanded(True)
                return found
        return None
# ===========================================================================
# Timeline
# ===========================================================================

class TimelinePage(Page):
    """Month / weekday / hour-of-day distributions."""

    CHARTS = [
        ("month", "Files Modified per Month", "calendar",
         "Storage weight by month (last 24)", "modified_timeline", "month"),
        ("dow", "Files Modified per Weekday", "clock",
         "Aggregate storage by day of week", "day_of_week_distribution", "day"),
        ("hour", "Files Modified per Hour", "activity",
         "Storage weight by hour of day", "hour_of_day_distribution", "hour"),
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        _scroll, root = self.scroll_body()
        self._views: Dict[str, ChartView] = {}

        for key, title, icon, subtitle, attr, _label in self.CHARTS:
            panel = GlassPanel(title, icon, subtitle)
            view = ChartView(lambda a=attr: self._build(a))
            self._views[key] = view
            panel.add(view)
            root.addWidget(panel)

    def _build(self, attr: str):
        r = self._result
        if r is None or not r.has_data:
            return None
        rows = getattr(r, attr, [])
        if not rows:
            return None
        label_key = next(c[5] for c in self.CHARTS if c[4] == attr)
        return _bars(rows, "size", label_key)

    def set_empty(self) -> None:
        for view in self._views.values():
            view.rebuild()

    def set_result(self, result: AnalysisResult) -> None:
        self._result = result
        for view in self._views.values():
            view.rebuild()


# ===========================================================================
# Duplicates
# ===========================================================================

class DuplicatesPage(Page):
    """Hash-confirmed duplicate clusters with their wasted space."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        self.card_recover = StatCard("Recoverable", "â€”", "by removing copies",
                                     "duplicates", "red")
        self.card_groups = StatCard("Duplicate Groups", "â€”", "identical clusters",
                                    "layers", "amber")
        self.card_files = StatCard("Files Involved", "â€”", "across all groups",
                                   "files", "violet")
        root.addLayout(self.card_grid(
            [self.card_recover, self.card_groups, self.card_files], columns=3))

        panel = GlassPanel("Duplicate Storage Detection", "duplicates",
                           "Groups of byte-identical files")
        self.dup_badge = panel.set_badge("â€” groups")

        self.summary = QLabel("No duplicate detection has been run yet.")
        self.summary.setWordWrap(True)
        self.summary.setStyleSheet(
            f"color: {tokens().text_dim}; font-size: 13px; font-weight: 500;")
        panel.add(self.summary)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(
            ["File / Redundant Copy", "Location", "Size", "Modified"])
        self.tree.setAlternatingRowColors(True)
        self.tree.setWordWrap(False)
        self.tree.setRootIsDecorated(True)
        self.tree.setIndentation(20)
        self.tree.setUniformRowHeights(True)
        panel.add(self.tree, 1)
        root.addWidget(panel, 1)

    def set_empty(self) -> None:
        self.tree.clear()
        self.dup_badge.setText("â€” groups")
        for card in (self.card_recover, self.card_groups, self.card_files):
            card.set_value("â€”", animate=False)
        self.summary.setText("No duplicate detection has been run yet.")

    def set_result(self, result: AnalysisResult) -> None:
        self.tree.clear()
        groups = result.duplicate_groups
        involved = sum(g["count"] for g in groups)
        self.card_recover.set_value(
            result.duplicate_wasted_formatted if groups else "0 B",
            f"{len(groups)} cluster(s)")
        self.card_groups.set_value(f"{len(groups):,}")
        self.card_files.set_value(f"{involved:,}")
        self.dup_badge.setText(f"{len(groups)} groups")

        if not groups:
            self.summary.setText(
                "No duplicate files were found in this directory.")
            return
        self.summary.setText(
            f"Found <b>{len(groups)}</b> duplicate group(s) â€” approximately "
            f"<b style='color:#fca5a5'>{result.duplicate_wasted_formatted}</b> "
            f"could be recovered by keeping one copy of each group.")

        group_icon = get_svg_icon("duplicates", color="#f87171", size=16)
        for group in groups:
            top = QTreeWidgetItem([
                f"{group['count']} copies Â· {group['size_formatted']} each",
                f"Wasted: {group['wasted_formatted']}", "", ""])
            top.setIcon(0, group_icon)
            self.tree.addTopLevelItem(top)
            for record in group["files"]:
                child = QTreeWidgetItem([
                    "  " + record["name"], record["parent"],
                    record["size_formatted"], record["modified_formatted"]])
                child.setIcon(0, get_category_svg_icon(
                    record.get("type", "Other"), size=16))
                child.setData(0, Qt.ItemDataRole.UserRole,
                              record.get("path", ""))
                top.addChild(child)
        self.tree.expandToDepth(0)
# ===========================================================================
# Advanced diagnostics
# ===========================================================================

class AdvancedPage(Page):
    """Junk, name collisions, deep nesting, long paths, MIME, extensionless."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._viewer_callback: Optional[Callable[[str], None]] = None
        _scroll, root = self.scroll_body()

        self.card_junk = StatCard("Junk Candidates", "â€”", "temp / cache files",
                                  "trash", "red")
        self.card_name_dupes = StatCard("Name Collisions", "â€”",
                                        "same name, diff folder", "copy", "amber")
        self.card_deep = StatCard("Deep Files", "â€”", "nested beyond threshold",
                                  "layers", "violet")
        self.card_long = StatCard("Long Paths", "â€”", "beyond safe limits",
                                  "alert-circle", "amber")
        self.card_non_ascii = StatCard("Non-ASCII Names", "â€”",
                                       "may break tooling", "code", "cyan")
        self.card_children = StatCard("Busiest Folders", "â€”",
                                      "files per directory", "folder", "blue")
        self._cards = (self.card_junk, self.card_name_dupes, self.card_deep,
                       self.card_long, self.card_non_ascii, self.card_children)
        root.addLayout(self.card_grid(list(self._cards), columns=3))

        p1 = GlassPanel("Filename Collisions", "copy",
                        "Same filename found in multiple directories")
        self.dup_badge = p1.set_badge("0")
        self.dup_table = make_table(
            ["Filename", "Copies", "Total Size", "Example Path"])
        p1.add(FilterBar(self.dup_table, "Filter colliding namesâ€¦"))
        p1.add(self.dup_table, 1)
        _wire_open_in_viewer(self.dup_table, self._open_in_viewer)
        root.addWidget(p1)

        p2 = GlassPanel("Junk / Temp / Cache Candidates", "trash",
                        "Old temporary or backup files safe to review")
        self.junk_badge = p2.set_badge("0")
        self.junk_table = make_table(
            ["Name", "Location", "Type", "Size", "Age (days)"])
        p2.add(FilterBar(self.junk_table, "Filter junk filesâ€¦"))
        p2.add(self.junk_table, 1)
        _wire_open_in_viewer(self.junk_table, self._open_in_viewer)
        root.addWidget(p2)

        two = QHBoxLayout()
        two.setSpacing(14)

        p3 = GlassPanel("Deeply Nested Files", "layers",
                        "Beyond the configured depth threshold")
        self.deep_badge = p3.set_badge("0")
        self.deep_table = make_table(["Name", "Location", "Depth", "Size"])
        p3.add(FilterBar(self.deep_table, "Filter nested filesâ€¦"))
        p3.add(self.deep_table, 1)
        _wire_open_in_viewer(self.deep_table, self._open_in_viewer)
        two.addWidget(p3)

        p4 = GlassPanel("Long Paths", "alert-circle",
                        "Paths exceeding safe limits")
        self.long_badge = p4.set_badge("0")
        self.long_table = make_table(["Name", "Path Length", "Location"])
        p4.add(FilterBar(self.long_table, "Filter long pathsâ€¦"))
        p4.add(self.long_table, 1)
        two.addWidget(p4)
        root.addLayout(two)

        two2 = QHBoxLayout()
        two2.setSpacing(14)

        p5 = GlassPanel("MIME Summary", "database",
                        "Distribution by top-level media type")
        self.mime_table = make_table(["MIME", "Files", "Size", "% Share"])
        p5.add(self.mime_table, 1)
        two2.addWidget(p5)

        p6 = GlassPanel("Files Without Extension", "files",
                        "Scripts, configs or unknown binaries")
        self.extless_badge = p6.set_badge("0")
        self.extless_table = make_table(["Name", "Location", "Size"])
        p6.add(FilterBar(self.extless_table, "Filter extension-less filesâ€¦"))
        p6.add(self.extless_table, 1)
        _wire_open_in_viewer(self.extless_table, self._open_in_viewer)
        two2.addWidget(p6)
        root.addLayout(two2)

        p7 = GlassPanel("Busiest Directories", "folder",
                        "Directories holding the most files directly")
        self.children_badge = p7.set_badge("0")
        self.children_table = make_table(
            ["Directory", "Direct Files", "Size"])
        p7.add(FilterBar(self.children_table, "Filter directoriesâ€¦"))
        p7.add(self.children_table, 1)
        root.addWidget(p7)

    def set_viewer_callback(self, cb: Callable[[str], None]) -> None:
        """Register the callback used to open a file in the viewer."""
        self._viewer_callback = cb

    def _open_in_viewer(self, path: str) -> None:
        if self._viewer_callback:
            self._viewer_callback(path)

    def set_empty(self) -> None:
        for card in self._cards:
            card.set_value("â€”", animate=False)
        for table in (self.dup_table, self.junk_table, self.deep_table,
                      self.long_table, self.mime_table, self.extless_table,
                      self.children_table):
            fill_table(table, [])
        for badge in (self.dup_badge, self.junk_badge, self.deep_badge,
                      self.long_badge, self.extless_badge, self.children_badge):
            badge.setText("0")

    def set_result(self, result: AnalysisResult) -> None:
        if not result.has_data:
            self.set_empty()
            return

        junk_size = sum(j["size"] for j in result.potential_junk)
        self.card_junk.set_value(
            f"{len(result.potential_junk):,}",
            f"{format_size(junk_size)} recoverable")
        self.card_name_dupes.set_value(f"{len(result.filename_duplicates):,}")
        self.card_deep.set_value(f"{len(result.deep_files):,}")
        self.card_long.set_value(f"{len(result.long_path_files):,}")
        self.card_non_ascii.set_value(f"{len(result.non_ascii_files):,}")
        self.card_children.set_value(f"{len(result.directory_children):,}")

        rows = []
        for entry in result.filename_duplicates[:200]:
            example = entry["files"][0]["parent"] if entry.get("files") else ""
            item = QTableWidgetItem(entry["name"])
            if entry.get("files"):
                item.setData(Qt.ItemDataRole.UserRole,
                             entry["files"][0].get("path", ""))
            rows.append([item, f"{entry['count']}",
                         entry["size_formatted"], example])
        fill_table(self.dup_table, rows)
        self.dup_badge.setText(f"{len(result.filename_duplicates)}")

        rows = []
        for entry in result.potential_junk:
            item = QTableWidgetItem(entry["name"])
            item.setData(Qt.ItemDataRole.UserRole, entry.get("path", ""))
            rows.append([item, entry.get("parent", ""), entry.get("type", "Other"),
                         entry["size_formatted"], f"{entry.get('age_days', 0):,}"])
        fill_table(self.junk_table, rows)
        self.junk_badge.setText(f"{len(result.potential_junk)}")

        rows = []
        for entry in result.deep_files:
            item = QTableWidgetItem(entry["name"])
            item.setData(Qt.ItemDataRole.UserRole, entry.get("path", ""))
            rows.append([item, entry.get("parent", ""),
                         f"{entry.get('depth', 0)}", entry["size_formatted"]])
        fill_table(self.deep_table, rows)
        self.deep_badge.setText(f"{len(result.deep_files)}")

        fill_table(self.long_table, section_rows(
            result.long_path_files, ("name", "path_len", "parent")))
        self.long_badge.setText(f"{len(result.long_path_files)}")

        fill_table(self.mime_table, section_rows(
            result.mime_summary,
            ("mime", "files", "size_formatted", "percentage")))

        rows = []
        for entry in result.extensionless_files:
            item = QTableWidgetItem(entry["name"])
            item.setData(Qt.ItemDataRole.UserRole, entry.get("path", ""))
            rows.append([item, entry.get("parent", ""), entry["size_formatted"]])
        fill_table(self.extless_table, rows)
        self.extless_badge.setText(f"{len(result.extensionless_files)}")

        fill_table(self.children_table, section_rows(
            result.directory_children, ("name", "children", "size_formatted")))
        self.children_badge.setText(f"{len(result.directory_children)}")
# ===========================================================================
# Deep insights
# ===========================================================================

class InsightsPage(Page):
    """Ranked recommendations, key insights, hierarchy and warnings."""

    SEVERITY = {
        "critical": "warning",
        "warning": "alert-circle",
        "archive": "archive",
        "notice": "info",
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        _scroll, root = self.scroll_body()

        panel_rec = GlassPanel(
            "Actionable Optimization Recommendations", "sparkles",
            "Ranked by impact on your storage footprint")
        self.rec_box = QVBoxLayout()
        self.rec_box.setSpacing(8)
        panel_rec.body.addLayout(self.rec_box)
        root.addWidget(panel_rec, 3)

        panel_ins = GlassPanel("Key Insights & Storage Telemetry", "insights",
                               "Automatic observations from the analysis")
        self.ins_box = QVBoxLayout()
        self.ins_box.setSpacing(6)
        panel_ins.body.addLayout(self.ins_box)
        root.addWidget(panel_ins, 3)

        panel_tree = GlassPanel("Directory Hierarchy", "folder",
                                "Top-level structure preview")
        self.tree_view = QLabel()
        self.tree_view.setObjectName("TreeBox")
        self.tree_view.setTextFormat(Qt.TextFormat.PlainText)
        self.tree_view.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.tree_view.setMinimumHeight(180)
        self.tree_view.setMaximumHeight(340)
        panel_tree.body.addWidget(self.tree_view)
        root.addWidget(panel_tree, 2)

        self.warnings = QLabel()
        self.warnings.setWordWrap(True)
        self.warnings.setStyleSheet(
            f"color: {tokens().danger}; font-size: 12px; font-weight: 600;")
        root.addWidget(self.warnings)

    @staticmethod
    def _clear(layout: QVBoxLayout) -> None:
        """Remove and delete every widget currently in ``layout``."""
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def set_empty(self) -> None:
        for layout in (self.rec_box, self.ins_box):
            self._clear(layout)
            layout.addWidget(EmptyState(
                "Nothing to report yet",
                "Run a scan to generate recommendations and insights.",
                "insights"))
        self.tree_view.setText("â€”")
        self.warnings.setText("")

    def set_result(self, result: AnalysisResult) -> None:
        if not result.has_data:
            self.set_empty()
            return

        self._clear(self.rec_box)
        rec_cards: List[InsightCard] = []
        for rec in result.actionable_recommendations:
            severity = rec["type"].lower()
            icon = self.SEVERITY.get(severity, "info")
            prop = severity if severity in self.SEVERITY else "info"
            rec_cards.append(InsightCard(
                prop, icon,
                f"<b>[{rec['type']}] {rec['title']}</b><br/>{rec['action']}"))
        if not rec_cards:
            rec_cards.append(InsightCard(
                "success", "check-circle",
                "No storage warnings. Everything is in optimal condition."))
        for card in rec_cards:
            self.rec_box.addWidget(card)

        self._clear(self.ins_box)
        for ins in result.key_insights:
            self.ins_box.addWidget(InsightCard(
                "info", "check-circle", str(ins).replace("**", "")))

        self.tree_view.setText(result.tree_text or "â€”")
        self.warnings.setText(
            "  âš   " + "  Â·  ".join(result.warnings) if result.warnings else "")

        if not reduced_motion():
            stagger_in(rec_cards, step=40)
# ===========================================================================
# Reports (unified export frame)
# ===========================================================================

class ReportsPage(Page):
    """One frame for choosing formats, exporting and opening the output.

    This replaces the old Export page. The export itself runs on a worker
    thread (:class:`~ui.export_worker.ExportWorker`) and is driven by the
    window, which shows an animated :class:`~ui.modals.ExportOverlay`. This
    page only collects intent and reports the outcome.
    """

    FORMATS = [
        ("html", "export", "HTML Dashboard",
         "Self-contained glass dashboard with animated SVG charts"),
        ("md", "document", "Markdown Summary",
         "Executive Markdown with tables, insights and diagnostics"),
        ("json", "database", "JSON Data",
         "Full structured telemetry for programmatic use"),
        ("csv", "charts", "CSV Breakdown",
         "File-type table for Excel, Sheets or Power BI"),
        ("txt", "files", "Plain Text",
         "Human-readable summary for terminals and logs"),
    ]

    #: One-click presets; the value is the set of format keys it selects.
    PRESETS = {"Minimal": ["txt"],
               "Analyst": ["csv", "json"],
               "Share": ["html", "md"],
               "Everything": ["html", "md", "json", "csv", "txt"]}

    exportRequested = Signal(str, list)      # output dir, format keys
    openFolderRequested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        _scroll, root = self.scroll_body()

        self.result: Optional[AnalysisResult] = None
        self._last_dir = ""

        picker = GlassPanel("Choose Report Formats", "export",
                            "Pick the formats to generate for the current scan")
        self.export_badge = picker.set_badge("no data")
        self.cards: Dict[str, CheckCard] = {}

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
        for i, (key, icon, title, body) in enumerate(self.FORMATS):
            card = CheckCard(title, body, icon, checked=True)
            self.cards[key] = card
            grid.addWidget(card, i // 2, i % 2)
        picker.body.addLayout(grid)

        preset_row = QHBoxLayout()
        preset_row.setSpacing(8)
        preset_label = QLabel("Presets")
        preset_label.setObjectName("SectionTitle")
        preset_row.addWidget(preset_label)
        self.preset_control = SegmentedControl(list(self.PRESETS), "Everything")
        self.preset_control.changed.connect(self._apply_preset)
        preset_row.addWidget(self.preset_control)
        preset_row.addStretch(1)
        picker.body.addLayout(preset_row)
        root.addWidget(picker)

        dest = GlassPanel("Output Location", "folder",
                          "Where the generated reports are written")
        self.dir_edit = QLineEdit()
        self.dir_edit.setPlaceholderText(
            "Defaults to 'folder_analysis' inside the scanned folder")
        browse = QPushButton("Browseâ€¦")
        browse.setObjectName("GhostButton")
        browse.setIcon(get_svg_icon("folder", color="#cbd5e1", size=16))
        browse.clicked.connect(self._browse)
        dest.body.addWidget(self.dir_edit)
        dest.body.addWidget(browse, 0, Qt.AlignmentFlag.AlignLeft)
        root.addWidget(dest)

        actions = GlassPanel("Generate", "zap", "Reports run off the UI thread")
        self.export_btn = QPushButton("  Export Reports")
        self.export_btn.setObjectName("RunButton")
        self.export_btn.setIcon(get_svg_icon("download", color="#ffffff", size=18))
        self.export_btn.setIconSize(QSize(18, 18))
        self.export_btn.setMinimumHeight(40)
        self.export_btn.setToolTip("Generate the selected reports  (Ctrl+S)")
        self.export_btn.clicked.connect(self._emit_export)
        actions.body.addWidget(self.export_btn)

        self.status = QLabel("Run a scan first to enable exports.")
        self.status.setWordWrap(True)
        self.status.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)
        self.status.setStyleSheet(
            f"color: {tokens().text_dim}; font-size: 12px;")
        actions.body.addWidget(self.status)

        self.open_btn = QPushButton("  Open Output Folder")
        self.open_btn.setObjectName("GhostButton")
        self.open_btn.setIcon(get_svg_icon("external", color="#60a5fa", size=16))
        self.open_btn.setVisible(False)
        self.open_btn.clicked.connect(
            lambda: self.openFolderRequested.emit(self._last_dir))
        actions.body.addWidget(self.open_btn, 0, Qt.AlignmentFlag.AlignLeft)
        root.addWidget(actions)
        root.addStretch(1)

    # -- state -------------------------------------------------------------

    def set_empty(self) -> None:
        self.result = None
        self.export_badge.setText("no data")
        self.export_btn.setEnabled(False)
        self.status.setText("Run a scan first to enable exports.")
        self.open_btn.setVisible(False)

    def set_result(self, result: AnalysisResult) -> None:
        self.result = result
        if not result.has_data:
            self.set_empty()
            return
        self.export_badge.setText(f"{result.total_files:,} files")
        self.export_btn.setEnabled(True)
        self.status.setText(
            f"Ready to export â€” {result.total_files:,} files indexed "
            f"({result.total_storage_formatted}).")
        if not self.dir_edit.text().strip():
            self.dir_edit.setPlaceholderText(
                os.path.join(result.root_path, "folder_analysis"))

    def set_busy(self, busy: bool) -> None:
        """Reflect an in-flight export on the button."""
        has_data = self.result is not None and self.result.has_data
        self.export_btn.setEnabled(not busy and has_data)
        self.export_btn.setText("  Exportingâ€¦" if busy else "  Export Reports")

    def report_done(self, written: List[str], output_dir: str) -> None:
        """Record a successful export for display and later reopening."""
        self._last_dir = output_dir
        self.open_btn.setVisible(True)
        self.export_badge.setText(f"{len(written)} files")
        lines = [f"Exported {len(written)} report(s) to:"]
        lines += [f"  â€¢  {os.path.basename(p)}" for p in written]
        self.status.setText("<br>".join(lines))

    def report_failed(self, message: str) -> None:
        """Record a failed export."""
        self.open_btn.setVisible(False)
        self.status.setText(f"Export failed: {message}")

    def selected_formats(self) -> List[str]:
        """Format keys whose check card is ticked."""
        return [key for key, card in self.cards.items() if card.is_checked()]

    def output_dir(self) -> str:
        """Resolve the effective output directory."""
        typed = self.dir_edit.text().strip()
        if typed:
            return os.path.abspath(os.path.expanduser(typed))
        root = self.result.root_path if self.result else ""
        return os.path.join(root, "folder_analysis") if root else ""

    # -- interactions ------------------------------------------------------

    def _apply_preset(self, name: str) -> None:
        """Tick exactly the format cards the preset covers."""
        keys = self.PRESETS.get(name)
        if keys is None:
            return
        for key, card in self.cards.items():
            card.set_checked(key in keys)

    def _browse(self) -> None:
        start = self.dir_edit.text() or os.path.expanduser("~")
        chosen = QFileDialog.getExistingDirectory(
            self, "Choose output folder", start)
        if chosen:
            self.dir_edit.setText(chosen)

    def _emit_export(self) -> None:
        """Validate the selection and ask the window to start the export."""
        formats = self.selected_formats()
        if not formats:
            self.status.setText("Select at least one report format above.")
            return
        if self.result is None or not self.result.has_data:
            self.status.setText("Run a scan first to enable exports.")
            return
        self.exportRequested.emit(self.output_dir(), formats)
# ===========================================================================
# Settings
# ===========================================================================

class SettingsPage(Page):
    """Appearance and analysis preferences, applied live or on the next scan."""

    #: (config field, label, description) for the boolean analysis toggles.
    ANALYSIS_TOGGLES = [
        ("detect_duplicates", "Duplicate detection",
         "Hash files to find byte-identical copies (slowest but exact)"),
        ("detect_name_collisions", "Filename collisions",
         "Find the same filename reused across different folders"),
        ("detect_junk", "Junk / temp candidates",
         "Flag .tmp, .bak, .old, cache and download leftovers"),
        ("detect_long_paths", "Long path warnings",
         "Flag paths that risk MAX_PATH failures on Windows"),
        ("detect_non_ascii", "Non-ASCII names",
         "Flag filenames that may break scripts and tooling"),
        ("build_timeline", "Timeline analytics",
         "Build month / weekday / hour-of-day distributions"),
        ("include_hidden", "Include hidden entries",
         "Scan dot-files and hidden system directories"),
        ("follow_symlinks", "Follow symlinks",
         "Descend into directory symlinks (may loop or duplicate)"),
    ]

    #: (config field, label, min, max, step) for the numeric limits.
    LIMITS = [
        ("max_duplicate_size_mb", "Duplicate size cap (MB)", 1, 2048, 1),
        ("long_path_limit", "Long path threshold (chars)", 80, 1024, 10),
        ("top_n", "Entries per breakdown", 5, 200, 5),
        ("deep_depth_threshold", "Deep-nesting threshold", 2, 30, 1),
        ("junk_min_age_days", "Junk minimum age (days)", 0, 365, 5),
        ("tree_max_depth", "Directory tree depth", 1, 10, 1),
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        _scroll, root = self.scroll_body()
        self.manager = ThemeManager.instance()
        root.addWidget(self._build_appearance())
        root.addWidget(self._build_analysis())
        root.addWidget(self._build_limits())
        root.addWidget(self._build_about())

    # -- sections ----------------------------------------------------------

    def _build_appearance(self) -> GlassPanel:
        panel = GlassPanel("Appearance", "sparkles",
                           "Theme changes apply immediately")
        panel.set_badge(f"v{__version__}")

        grid = QGridLayout()
        grid.setSpacing(10)

        grid.addWidget(self._field_label("Theme"), 0, 0)
        self.theme_control = SegmentedControl(
            [THEMES[k].name for k in THEMES], THEMES[self.manager.tokens.key].name)
        self.theme_by_name = {v.name: k for k, v in THEMES.items()}
        self.theme_control.changed.connect(self._on_theme_picked)
        grid.addWidget(self.theme_control, 0, 1)

        grid.addWidget(self._field_label("Accent"), 1, 0)
        self.accent_control = SegmentedControl(list(ACCENTS), "Blue")
        self.accent_control.changed.connect(
            lambda name: self.manager.set_accent(ACCENTS[name]))
        grid.addWidget(self.accent_control, 1, 1)

        grid.addWidget(self._field_label("Density"), 2, 0)
        self.density_control = SegmentedControl(list(DENSITIES),
                                                self.manager.density)
        self.density_control.changed.connect(self.manager.set_density)
        grid.addWidget(self.density_control, 2, 1)
        panel.body.addLayout(grid)

        reset = QPushButton("Reset appearance")
        reset.setObjectName("GhostButton")
        reset.setIcon(get_svg_icon("refresh", color="#cbd5e1", size=16))
        reset.clicked.connect(self.manager.reset_appearance)
        panel.body.addWidget(reset, 0, Qt.AlignmentFlag.AlignLeft)
        return panel

    def _build_analysis(self) -> GlassPanel:
        panel = GlassPanel("Analysis Options", "sliders",
                           "Applied on the next scan")
        self.toggles: Dict[str, QCheckBox] = {}
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)
        for i, (field, label, description) in enumerate(self.ANALYSIS_TOGGLES):
            box = QCheckBox()
            box.setChecked(bool(getattr(self._config(), field, True)))
            box.setToolTip(description)
            self.toggles[field] = box
            grid.addWidget(self._toggle_card(label, description, box),
                           i // 2, i % 2)
        panel.body.addLayout(grid)
        return panel

    def _toggle_card(self, title: str, description: str,
                     box: QCheckBox) -> QFrame:
        card = QFrame()
        card.setObjectName("InsightCard")
        card.setProperty("severity", "info")
        lay = QHBoxLayout(card)
        lay.setContentsMargins(12, 9, 12, 9)
        lay.setSpacing(11)
        texts = QVBoxLayout()
        texts.setSpacing(1)
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            f"color: {tokens().text_strong}; font-size: 13px; font-weight: 600;")
        desc_lbl = QLabel(description)
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet(f"color: {tokens().text_dim}; font-size: 11px;")
        texts.addWidget(title_lbl)
        texts.addWidget(desc_lbl)
        lay.addLayout(texts, 1)
        lay.addWidget(box, 0, Qt.AlignmentFlag.AlignTop)
        return card

    def _build_limits(self) -> GlassPanel:
        panel = GlassPanel("Advanced Limits", "settings",
                           "Tuning knobs for very large or unusual folders")
        config = self._config()

        grid = QGridLayout()
        grid.setSpacing(10)
        self.spins: Dict[str, Any] = {}
        for row, (field, label, low, high, step) in enumerate(self.LIMITS):
            from PySide6.QtWidgets import QSpinBox
            spin = QSpinBox()
            spin.setRange(low, high)
            spin.setSingleStep(step)
            spin.setValue(int(getattr(config, field, low)))
            spin.valueChanged.connect(
                lambda value, f=field: self._set_config_field(f, value))
            self.spins[field] = spin
            grid.addWidget(self._field_label(label), row, 0)
            grid.addWidget(spin, row, 1)

        from PySide6.QtWidgets import QComboBox
        self.hash_combo = QComboBox()
        self.hash_combo.addItems(["md5", "sha1", "sha256"])
        self.hash_combo.setCurrentText(config.duplicate_hash_algorithm)
        self.hash_combo.currentTextChanged.connect(
            lambda value: self._set_config_field("duplicate_hash_algorithm",
                                                 value))
        last = len(self.LIMITS)
        grid.addWidget(self._field_label("Hash algorithm"), last, 0)
        grid.addWidget(self.hash_combo, last, 1)
        panel.body.addLayout(grid)
        return panel

    def _build_about(self) -> GlassPanel:
        panel = GlassPanel("About", "info",
                           "Folder Analysis Pro â€” storage analytics")
        info = QLabel(
            f"<b>Version {__version__}</b><br/>"
            "Pure-Python analysis engine with a PySide6 front end. Duplicate "
            "detection hashes files up to the configured size cap; unreadable "
            "folders are skipped and reported rather than aborting the scan.")
        info.setWordWrap(True)
        info.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)
        info.setStyleSheet(f"color: {tokens().text_dim}; font-size: 12px;")
        panel.body.addWidget(info)

        shortcuts = QPushButton("Keyboard shortcuts")
        shortcuts.setObjectName("GhostButton")
        shortcuts.setIcon(get_svg_icon("keyboard", color="#cbd5e1", size=16))
        shortcuts.clicked.connect(self._request_shortcuts)
        panel.body.addWidget(shortcuts, 0, Qt.AlignmentFlag.AlignLeft)
        return panel

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _field_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("StageDetail")
        return label

    def _config(self) -> AnalysisConfig:
        """The live analysis config owned by :mod:`ui.settings_store`."""
        from .settings_store import active_config
        return active_config()

    def _set_config_field(self, field: str, value: Any) -> None:
        setattr(self._config(), field, value)

    def _on_theme_picked(self, name: str) -> None:
        key = self.theme_by_name.get(name)
        if key:
            self.manager.set_theme(key)

    def _request_shortcuts(self) -> None:
        window = self.window()
        if hasattr(window, "_show_shortcuts"):
            window._show_shortcuts()

    # -- contract ----------------------------------------------------------

    def set_empty(self) -> None:
        """Settings do not depend on scan state."""

    def set_result(self, result: AnalysisResult) -> None:
        """Sync the controls with the config actually used by the scan."""
        config = self._config()
        for field, box in self.toggles.items():
            box.blockSignals(True)
            box.setChecked(bool(getattr(config, field, False)))
            box.blockSignals(False)
        for field, spin in self.spins.items():
            spin.blockSignals(True)
            spin.setValue(int(getattr(config, field, spin.minimum())))
            spin.blockSignals(False)
        lay = QHBoxLayout(card)
        lay.setContentsMargins(12, 9, 12, 9)
        lay.setSpacing(11)
        texts = QVBoxLayout()
        texts.setSpacing(1)
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            f"color: {tokens().text_strong}; font-size: 13px; font-weight: 600;")
        desc_lbl = QLabel(description)
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet(f"color: {tokens().text_dim}; font-size: 11px;")
        texts.addWidget(title_lbl)
        texts.addWidget(desc_lbl)
        lay.addLayout(texts, 1)
        lay.addWidget(box, 0, Qt.AlignmentFlag.AlignTop)
        return card
