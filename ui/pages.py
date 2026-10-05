"""
Page widgets for the main window with premium glassmorphism, SVG vector icons,
industrial-grade KPI cards, filterable tables, and severity-driven insights.

Every page exposes ``set_result(result)`` so the main window can push a fresh
:class:`AnalysisResult` into it after each scan.
"""

from __future__ import annotations

import os
from typing import Any, Callable, Dict, List, Optional

from PySide6.QtCore import (
    QEasingCurve, QPropertyAnimation, QSize, Qt,
)
from PySide6.QtGui import QColor, QFont, QIcon
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QFileDialog, QFrame, QGraphicsOpacityEffect,
    QGridLayout, QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QPushButton, QScrollArea, QSizePolicy,
    QTableWidget, QTableWidgetItem, QTabWidget, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QWidget,
)

from folder_analyzer.models import AnalysisResult
from .icons import get_category_svg_icon, get_svg_icon, get_svg_pixmap


# ===========================================================================
# Reusable components
# ===========================================================================

class StatCard(QFrame):
    """Rounded glass KPI card with accent stripe, icon badge, trend chip."""

    def __init__(self, title: str, value: str = "—", subtitle: str = "",
                 icon_name: str = "activity", accent: str = "blue",
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("StatCard")
        self.setProperty("accent", accent)
        self._accent_color = {
            "cyan": "#00d2ff", "blue": "#4f8cff", "violet": "#8b5cf6",
            "green": "#22c55e", "amber": "#f59e0b", "red": "#ef4444",
        }.get(accent, "#4f8cff")
        self._icon_name = icon_name

        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 14, 18, 14)
        outer.setSpacing(8)

        # Top row: icon badge + title + trend
        top = QHBoxLayout()
        top.setSpacing(10)

        self._icon_lbl = QLabel()
        self._icon_lbl.setFixedSize(28, 28)
        self._icon_lbl.setAlignment(Qt.AlignCenter)
        self._icon_lbl.setPixmap(get_svg_pixmap(icon_name, size=18,
                                                color=self._accent_color))
        self._icon_lbl.setStyleSheet(
            f"background: rgba(255,255,255,0.05); border-radius: 8px; "
            f"border: 1px solid rgba(255,255,255,0.06);"
        )
        top.addWidget(self._icon_lbl)

        title_lbl = QLabel(title.upper())
        title_lbl.setObjectName("StatCardTitle")
        top.addWidget(title_lbl)
        top.addStretch(1)

        self._trend = QLabel("")
        self._trend.setObjectName("StatCardTrend")
        self._trend.setVisible(False)
        top.addWidget(self._trend)

        outer.addLayout(top)

        # Value
        self._value = QLabel(value)
        self._value.setObjectName("StatCardValue")
        self._value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        outer.addWidget(self._value)

        # Subtitle
        self._sub = QLabel(subtitle)
        self._sub.setObjectName("StatCardSub")
        self._sub.setWordWrap(True)
        outer.addWidget(self._sub)

        outer.addStretch(1)

        # Pulse-in effect on update
        self._effect = QGraphicsOpacityEffect(self)
        self._effect.setOpacity(1.0)
        self.setGraphicsEffect(self._effect)

    def set_value(self, value: str, subtitle: Optional[str] = None,
                  trend: Optional[str] = None) -> None:
        """Update value (with fade-in pulse) and optional trend chip."""
        self._value.setText(value)
        if subtitle is not None:
            self._sub.setText(subtitle)

        if trend is None:
            self._trend.setVisible(False)
        else:
            self._trend.setText(trend)
            self._trend.setVisible(True)
            kind = "up" if trend.strip().startswith("↑") else \
                   "down" if trend.strip().startswith("↓") else "flat"
            self._trend.setProperty("trend", kind)
            self._trend.style().unpolish(self._trend)
            self._trend.style().polish(self._trend)

        self._anim = QPropertyAnimation(self._effect, b"opacity")
        self._anim.setDuration(320)
        self._anim.setStartValue(0.4)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.start()


class Panel(QFrame):
    """Titled glass panel with icon header, subtitle, optional right-side widget."""

    def __init__(self, title: str, icon_name: str = "layers",
                 subtitle: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("GlassPanel")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 16, 18, 16)
        outer.setSpacing(12)

        header = QHBoxLayout()
        header.setSpacing(10)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_svg_pixmap(icon_name, size=18, color="#93c5fd"))
        header.addWidget(icon_lbl)

        title_box = QVBoxLayout()
        title_box.setSpacing(1)
        self.title_lbl = QLabel(title)
        self.title_lbl.setObjectName("PanelTitle")
        title_box.addWidget(self.title_lbl)
        if subtitle:
            sub = QLabel(subtitle)
            sub.setObjectName("PanelSubtitle")
            title_box.addWidget(sub)
        header.addLayout(title_box)
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
        self.header_actions.addWidget(badge)
        return badge


def make_table(headers: List[str]) -> QTableWidget:
    """Create a read-only glass table with sortable headers."""
    table = QTableWidget(0, len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.verticalHeader().setVisible(False)
    table.setAlternatingRowColors(True)
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setSelectionMode(QAbstractItemView.SingleSelection)
    table.setWordWrap(False)
    table.setShowGrid(False)
    table.setSortingEnabled(True)
    table.horizontalHeader().setHighlightSections(False)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
    table.horizontalHeader().setStretchLastSection(True)
    return table


def fill_table(table: QTableWidget, rows: List[List[Any]]) -> None:
    """Replace table contents with rows (sorting temporarily disabled)."""
    table.setSortingEnabled(False)
    table.setRowCount(0)
    for row in rows:
        idx = table.rowCount()
        table.insertRow(idx)
        for col, val in enumerate(row):
            item = val if isinstance(val, QTableWidgetItem) else QTableWidgetItem(str(val))
            if not isinstance(val, QTableWidgetItem):
                if col > 0 and any(ch.isdigit() for ch in str(val)):
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            table.setItem(idx, col, item)
    if table.rowCount():
        table.resizeColumnsToContents()
        if table.columnCount() > 0:
            table.setColumnWidth(0, max(table.columnWidth(0), 200))
    table.setSortingEnabled(True)


class FilterBar(QWidget):
    """Small search field with icon used above tables."""

    def __init__(self, table: QTableWidget, placeholder: str = "Filter rows…",
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._table = table
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_svg_pixmap("search", size=14, color="#64748b"))
        lay.addWidget(icon_lbl)

        self.input = QLineEdit()
        self.input.setPlaceholderText(placeholder)
        self.input.setClearButtonEnabled(True)
        self.input.textChanged.connect(self._apply)
        lay.addWidget(self.input, 1)

        self.count_lbl = QLabel("")
        self.count_lbl.setObjectName("PanelSubtitle")
        lay.addWidget(self.count_lbl)

    def _apply(self, text: str) -> None:
        needle = text.lower().strip()
        visible = 0
        for r in range(self._table.rowCount()):
            row_match = False
            for c in range(self._table.columnCount()):
                it = self._table.item(r, c)
                if it and needle in it.text().lower():
                    row_match = True
                    break
            self._table.setRowHidden(r, not row_match)
            if row_match:
                visible += 1
        total = self._table.rowCount()
        self.count_lbl.setText(f"{visible}/{total}" if needle else f"{total} rows")


class EmptyState(QWidget):
    """Big-icon centered empty state for charts/tables with no data."""

    def __init__(self, icon_name: str = "search",
                 title: str = "Nothing here yet",
                 body: str = "Run a scan to populate this view.",
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 40, 20, 40)
        lay.setSpacing(10)
        lay.setAlignment(Qt.AlignCenter)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_svg_pixmap(icon_name, size=44, color="#3f5068"))
        icon_lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(icon_lbl)

        t = QLabel(title)
        t.setObjectName("EmptyStateTitle")
        t.setAlignment(Qt.AlignCenter)
        lay.addWidget(t)

        b = QLabel(body)
        b.setObjectName("EmptyStateBody")
        b.setAlignment(Qt.AlignCenter)
        b.setWordWrap(True)
        lay.addWidget(b)


# ===========================================================================
# Overview page
# ===========================================================================

class OverviewPage(QWidget):
    """Headline metrics + storage health + actionable recommendations + file types."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)

        # KPI Row 1: three primary cards
        row1 = QHBoxLayout()
        row1.setSpacing(12)
        self.card_files = StatCard("Files Indexed", "—", "0-byte: —",
                                   icon_name="files", accent="blue")
        self.card_dirs = StatCard("Directories", "—", "Branches scanned",
                                  icon_name="folder", accent="violet")
        self.card_size = StatCard("Total Storage", "—", "Disk footprint",
                                  icon_name="hard-drive", accent="cyan")
        for c in (self.card_files, self.card_dirs, self.card_size):
            row1.addWidget(c, 1)
        root.addLayout(row1)

        # KPI Row 2: secondary cards
        row2 = QHBoxLayout()
        row2.setSpacing(12)
        self.card_avg = StatCard("Average File", "—", "Mean size",
                                 icon_name="charts", accent="violet")
        self.card_health = StatCard("Health Score", "—", "Storage efficiency",
                                    icon_name="health", accent="green")
        self.card_dupes = StatCard("Duplicate Waste", "—", "Recoverable",
                                   icon_name="duplicates", accent="red")
        for c in (self.card_avg, self.card_health, self.card_dupes):
            row2.addWidget(c, 1)
        root.addLayout(row2)

        # Recommendation banner
        self.action_box = QFrame()
        self.action_box.setObjectName("InsightCard")
        act_lay = QHBoxLayout(self.action_box)
        act_lay.setContentsMargins(14, 10, 14, 10)
        act_lay.setSpacing(12)
        self.action_icon = QLabel()
        self.action_icon.setPixmap(get_svg_pixmap("sparkles", size=22, color="#38bdf8"))
        act_lay.addWidget(self.action_icon)
        self.action_text = QLabel(
            "Run an analysis on any folder to see immediate storage recovery tips.")
        self.action_text.setStyleSheet(
            "color: #e2e8f0; font-size: 13px; font-weight: 500;")
        self.action_text.setWordWrap(True)
        act_lay.addWidget(self.action_text, 1)
        root.addWidget(self.action_box)

        # File-type panel
        panel = Panel("Storage Distribution by File Extension",
                      icon_name="files",
                      subtitle="Ranked by aggregate size")
        self.type_badge = panel.set_badge("— extensions")

        self.type_table = make_table(
            ["Extension", "Category", "Files", "Size", "% of storage"])
        panel.body.addWidget(FilterBar(self.type_table))
        panel.body.addWidget(self.type_table, 1)

        root.addWidget(panel, 1)

        self._empty_state()

    def _empty_state(self) -> None:
        for c in (self.card_files, self.card_dirs, self.card_size,
                  self.card_avg, self.card_health, self.card_dupes):
            c.set_value("—")
        self.card_health.set_value("—", "Storage efficiency")
        self.card_dupes.set_value("—", "Potential recovery")
        self.action_text.setText(
            "Run an analysis on any folder to view immediate storage recovery tips.")
        fill_table(self.type_table, [])
        self.type_badge.setText("— extensions")

    def set_result(self, result: AnalysisResult) -> None:
        if not result.has_data:
            self._empty_state()
            return

        self.card_files.set_value(
            f"{result.total_files:,}",
            f"{result.empty_files_count} zero-byte file(s)")
        self.card_dirs.set_value(f"{result.total_directories:,}")
        self.card_size.set_value(result.total_storage_formatted)
        self.card_avg.set_value(result.avg_file_size_formatted)

        score = result.storage_efficiency_score
        trend = "↑ Healthy" if score >= 80 else \
                "• Fair" if score >= 60 else "↓ Needs attention"
        self.card_health.set_value(f"{score}/100", result.storage_health_label, trend)

        self.card_dupes.set_value(
            result.duplicate_wasted_formatted if result.duplicate_groups else "0 B",
            f"{len(result.duplicate_groups)} duplicate cluster(s)")

        if result.actionable_recommendations:
            top = result.actionable_recommendations[0]
            self.action_text.setText(
                f"<b>Recommendation ({top['type']}):</b> "
                f"{top['title']} — {top['action']}")
        else:
            self.action_text.setText(
                "<b>Optimal Layout:</b> Directory storage is well organized with "
                "no detected duplicate waste.")

        rows = []
        for d in result.file_types:
            icon = get_category_svg_icon(d["category"], size=16)
            item_ext = QTableWidgetItem(icon, "  " + d["label"])
            rows.append([
                item_ext,
                d["category"],
                f"{d['files']:,}",
                d["size_formatted"],
                f"{d['percentage']}%",
            ])
        fill_table(self.type_table, rows)
        self.type_badge.setText(f"{len(result.file_types)} extensions")


# ===========================================================================
# Charts page (QtCharts)
# ===========================================================================

def _donut(entries: List[Dict[str, Any]], value_key: str = "size",
           label_key: str = "label", max_slices: int = 8):
    from PySide6.QtCore import QMargins
    from PySide6.QtGui import QColor
    from PySide6.QtCharts import QChart, QPieSeries

    rows = entries[:max_slices]
    if len(entries) > max_slices:
        rest = sum(d.get(value_key, 0) for d in entries[max_slices:])
        rows = rows + [{label_key: "Other", value_key: rest, "color": "#64748b"}]
    total = sum(d.get(value_key, 0) for d in rows) or 1

    series = QPieSeries()
    series.setPieSize(0.78)
    series.setHoleSize(0.5)
    for d in rows:
        val = float(d.get(value_key, 0))
        s = series.append(str(d.get(label_key, "?")), val)
        s.setBrush(QColor(d.get("color", "#4f8cff")))
        s.setLabelVisible(total > 0 and val / total >= 0.06)
        s.setLabelColor(QColor("#e2e8f0"))
        s.setBorderColor(QColor("rgba(15,22,38,0.9)"))

    chart = QChart()
    chart.setTheme(QChart.ChartTheme.ChartThemeDark)
    chart.setAnimationOptions(QChart.AnimationOption.AllAnimations)
    chart.setAnimationDuration(700)
    chart.setAnimationEasingCurve(QEasingCurve.OutCubic)
    chart.addSeries(series)
    chart.legend().setVisible(True)
    chart.legend().setAlignment(Qt.AlignBottom)
    chart.legend().setLabelColor(QColor("#cbd5e1"))
    chart.setBackgroundVisible(False)
    chart.setMargins(QMargins(6, 6, 6, 6))
    return chart


def _bars(entries: List[Dict[str, Any]], value_key: str = "size",
          label_key: str = "name", color: str = "#4f8cff"):
    from PySide6.QtGui import QColor, QFont
    from PySide6.QtCharts import (
        QBarCategoryAxis, QBarSeries, QBarSet, QChart, QValueAxis,
    )

    labels = [str(d.get(label_key, "?")) for d in entries]
    values = [float(d.get(value_key, 0)) for d in entries]

    bar_set = QBarSet("")
    bar_set.setColor(QColor(color))
    bar_set.append(values) if values else bar_set.append([0.0])
    series = QBarSeries()
    series.append(bar_set)
    series.setBarWidth(0.55)

    axis_x = QBarCategoryAxis()
    axis_x.append(labels)
    axis_x.setLabelsColor(QColor("#cbd5e1"))
    axis_x.setGridLineVisible(False)

    axis_y = QValueAxis()
    axis_y.setLabelFormat("%.0f")
    axis_y.setLabelsColor(QColor("#94a3b8"))
    axis_y.setGridLineColor(QColor("rgba(255,255,255,0.06)"))
    max_v = max(values) if values else 1.0
    axis_y.setRange(0, max_v * 1.15 if max_v else 1)

    chart = QChart()
    chart.setTheme(QChart.ChartTheme.ChartThemeDark)
    chart.setAnimationOptions(QChart.AnimationOption.AllAnimations)
    chart.setAnimationDuration(700)
    chart.setAnimationEasingCurve(QEasingCurve.OutCubic)
    chart.addSeries(series)
    chart.setAxisX(axis_x, series)
    chart.setAxisY(axis_y, series)
    chart.legend().setVisible(False)
    chart.setBackgroundVisible(False)
    return chart


class ChartsPage(QWidget):
    """Live visual analytics: types, categories, directory hotspots, age & size."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        from PySide6.QtCharts import QChartView
        from PySide6.QtGui import QPainter

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; }")

        inner = QWidget()
        scroll.setWidget(inner)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        root = QGridLayout(inner)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)

        def _view():
            v = QChartView()
            v.setRenderHint(QPainter.RenderHint.Antialiasing)
            v.setMinimumHeight(240)
            return v

        self._view_type = _view()
        self._view_cat = _view()
        self._view_dirs = _view()
        self._view_age = _view()
        self._view_size = _view()

        panel_type = Panel("Storage by File Type", "files",
                           "Top 8 extensions, size-weighted")
        panel_type.body.addWidget(self._view_type)

        panel_cat = Panel("Storage by Category", "layers",
                          "Grouped by media class")
        panel_cat.body.addWidget(self._view_cat)

        panel_dirs = Panel("Top Directories", "folder",
                           "Highest aggregate footprint")
        panel_dirs.body.addWidget(self._view_dirs)

        panel_age = Panel("File Age Distribution", "clock",
                          "Recency buckets")
        panel_age.body.addWidget(self._view_age)

        panel_size = Panel("File Size Distribution", "activity",
                           "Size class breakdown")
        panel_size.body.addWidget(self._view_size)

        root.addWidget(panel_type, 0, 0)
        root.addWidget(panel_cat, 0, 1)
        root.addWidget(panel_dirs, 1, 0, 1, 2)
        root.addWidget(panel_age, 2, 0)
        root.addWidget(panel_size, 2, 1)
        root.setRowStretch(1, 2)
        root.setColumnStretch(0, 1)
        root.setColumnStretch(1, 1)

    def set_result(self, result: AnalysisResult) -> None:
        self._view_type.setChart(_donut(result.file_types, "size", "label", 8))
        self._view_cat.setChart(_donut(result.categories, "size", "name", 9))
        self._view_dirs.setChart(
            _bars(result.top_directories[:10], "size", "name", "#3b82f6"))
        self._view_age.setChart(
            _bars(result.age_distribution, "size", "category", "#06b6d4"))
        self._view_size.setChart(
            _bars(result.size_distribution, "count", "range", "#a855f7"))


# ===========================================================================
# Files page
# ===========================================================================

class FilesPage(QWidget):
    """Largest files, oldest files, and 0-byte orphan files in tabbed tables."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        panel = Panel("File Explorer", "files",
                      "Deep dive into the largest, oldest, and empty files")
        self.file_badge = panel.set_badge("0 files")

        tabs = QTabWidget()
        self.table_largest = make_table(["Name", "Location", "Type", "Size", "Modified"])
        self.table_oldest = make_table(["Name", "Location", "Type", "Size", "Modified"])
        self.table_empty = make_table(["Name", "Location", "Type", "Size", "Modified"])

        for name, table in (("Largest Files", self.table_largest),
                            ("Oldest Files", self.table_oldest),
                            ("0-Byte Files", self.table_empty)):
            wrap = QWidget()
            wl = QVBoxLayout(wrap)
            wl.setContentsMargins(0, 6, 0, 0)
            wl.setSpacing(8)
            wl.addWidget(FilterBar(table))
            wl.addWidget(table, 1)
            tabs.addTab(wrap, name)

        panel.body.addWidget(tabs, 1)
        root.addWidget(panel, 1)

    def set_result(self, result: AnalysisResult) -> None:
        def build(records):
            out = []
            for r in records:
                cat = r.get("type", "Other") if isinstance(r, dict) else r.type
                name = r.get("name", "") if isinstance(r, dict) else r.name
                parent = r.get("parent", "") if isinstance(r, dict) else r.parent
                size_str = r.get("size_formatted", "") if isinstance(r, dict) else r.size_formatted
                mod_str = r.get("modified_formatted", "") if isinstance(r, dict) else r.modified_formatted
                icon = get_category_svg_icon(cat, size=16)
                name_item = QTableWidgetItem(icon, "  " + name)
                out.append([name_item, parent, cat, size_str, mod_str])
            return out

        fill_table(self.table_largest, build(result.largest_files))
        fill_table(self.table_oldest, build(result.oldest_files))
        fill_table(self.table_empty, build(result.empty_files_list))
        self.file_badge.setText(
            f"{len(result.largest_files) + len(result.oldest_files) + len(result.empty_files_list)} rows")


# ===========================================================================
# Duplicates page
# ===========================================================================

class DuplicatesPage(QWidget):
    """Duplicate groups with wasted-space summary and expandable tree."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        panel = Panel("Duplicate Storage Detection", "duplicates",
                      "Groups of identical files and their recoverable space")
        self.dup_badge = panel.set_badge("— groups")

        self.summary = QLabel("No duplicate detection has been run yet.")
        self.summary.setWordWrap(True)
        self.summary.setStyleSheet(
            "color: #94a3b8; font-size: 13px; font-weight: 500; padding: 0 2px;")
        panel.body.addWidget(self.summary)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["File / Redundant Copy", "Location", "Size", "Modified"])
        self.tree.setAlternatingRowColors(True)
        self.tree.setWordWrap(False)
        self.tree.setRootIsDecorated(True)
        self.tree.setIndentation(20)
        self.tree.setUniformRowHeights(True)
        panel.body.addWidget(self.tree, 1)

        root.addWidget(panel, 1)

    def set_result(self, result: AnalysisResult) -> None:
        self.tree.clear()
        if not result.duplicate_groups:
            self.summary.setText("No duplicate files were found in this directory.")
            self.dup_badge.setText("0 groups")
            return
        self.summary.setText(
            f"Found <b>{len(result.duplicate_groups)}</b> duplicate group(s) — "
            f"approximately <b style='color:#fca5a5'>"
            f"{result.duplicate_wasted_formatted}</b> could be recovered by "
            f"keeping one copy of each group."
        )
        self.dup_badge.setText(f"{len(result.duplicate_groups)} groups")

        group_icon = get_svg_icon("duplicates", color="#f87171", size=16)
        for group in result.duplicate_groups:
            top = QTreeWidgetItem([
                f"{group['count']} copies · {group['size_formatted']} each",
                f"Wasted space: {group['wasted_formatted']}", "", "",
            ])
            top.setIcon(0, group_icon)
            top.setFirstColumnSpanned(True)
            self.tree.addTopLevelItem(top)
            for f in group["files"]:
                file_icon = get_category_svg_icon(f.get("type", "Other"), size=16)
                child = QTreeWidgetItem([
                    "  " + f["name"], f["parent"],
                    f["size_formatted"], f["modified_formatted"],
                ])
                child.setIcon(0, file_icon)
                top.addChild(child)
        self.tree.expandToDepth(0)


# ===========================================================================
# Insights page
# ===========================================================================

class InsightsPage(QWidget):
    """Recommendations, key insights & hierarchy — with severity pills."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)

        # Recommendations
        panel_rec = Panel("Actionable Optimization Recommendations", "sparkles",
                          "Ranked by impact on storage footprint")
        self.rec_container = QVBoxLayout()
        self.rec_container.setSpacing(8)
        panel_rec.body.addLayout(self.rec_container)
        root.addWidget(panel_rec, 3)

        # Key insights
        panel_ins = Panel("Key Insights & Storage Telemetry", "insights",
                          "Automatic observations from the analysis")
        self.insights_container = QVBoxLayout()
        self.insights_container.setSpacing(6)
        panel_ins.body.addLayout(self.insights_container)
        root.addWidget(panel_ins, 3)

        # Directory tree
        panel_tree = Panel("Directory Hierarchy", "folder",
                           "Top-level structure preview")
        self.tree_view = QLabel()
        self.tree_view.setObjectName("TreeBox")
        self.tree_view.setTextFormat(Qt.PlainText)
        self.tree_view.setWordWrap(False)
        self.tree_view.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.tree_view.setMinimumHeight(180)
        self.tree_view.setMaximumHeight(360)
        panel_tree.body.addWidget(self.tree_view)
        root.addWidget(panel_tree, 2)

        self.warnings = QLabel()
        self.warnings.setWordWrap(True)
        self.warnings.setStyleSheet(
            "color: #f87171; font-size: 12px; font-weight: 600; padding: 4px;")
        root.addWidget(self.warnings)

    @staticmethod
    def _clear_layout(layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def _make_insight_card(self, severity: str, icon_name: str,
                           icon_color: str, text: str) -> QFrame:
        card = QFrame()
        card.setObjectName("InsightCard")
        card.setProperty("severity", severity)
        lay = QHBoxLayout(card)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(10)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_svg_pixmap(icon_name, size=16, color=icon_color))
        lay.addWidget(icon_lbl, 0, Qt.AlignTop)

        txt = QLabel(text)
        txt.setWordWrap(True)
        txt.setStyleSheet("color: #e2e8f0; font-size: 13px; font-weight: 500;")
        lay.addWidget(txt, 1)
        return card

    def set_result(self, result: AnalysisResult) -> None:
        # Recommendations
        self._clear_layout(self.rec_container)
        if result.actionable_recommendations:
            for rec in result.actionable_recommendations:
                sev = rec["type"].lower()
                icon = "warning" if sev == "critical" else \
                       "alert-circle" if sev == "warning" else "info"
                color = "#f87171" if sev == "critical" else \
                        "#fbbf24" if sev == "warning" else "#60a5fa"
                text = f"<b>[{rec['type']}] {rec['title']}</b><br/>{rec['action']}"
                self.rec_container.addWidget(
                    self._make_insight_card(sev, icon, color, text))
        else:
            self.rec_container.addWidget(
                self._make_insight_card(
                    "success", "check-circle", "#22c55e",
                    "No storage warnings. Everything is in optimal condition."))

        # Insights
        self._clear_layout(self.insights_container)
        for ins in result.key_insights:
            clean = ins.replace("**", "")
            self.insights_container.addWidget(
                self._make_insight_card(
                    "info", "check-circle", "#60a5fa", clean))

        # Tree + warnings
        self.tree_view.setText(result.tree_text or "—")
        self.warnings.setText(
            "  ⚠  " + "  ·  ".join(result.warnings) if result.warnings else "")


# ===========================================================================
# Export page
# ===========================================================================

class ExportPage(QWidget):
    """Choose formats and export styled reports with per-format cards."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.result: AnalysisResult | None = None

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; }")

        inner = QWidget()
        scroll.setWidget(inner)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        root = QVBoxLayout(inner)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)

        panel = Panel("Export Analytics & Reports", "export",
                      "Choose which formats to generate for the current scan")
        self.export_badge = panel.set_badge("ready")

        desc = QLabel(
            "Reports include a self-contained glassmorphic dashboard, "
            "structured telemetry, and executive summaries suitable for "
            "sharing or downstream analysis.")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #94a3b8; font-size: 12px; padding: 0 2px;")
        panel.body.addWidget(desc)

        formats_grid = QGridLayout()
        formats_grid.setHorizontalSpacing(10)
        formats_grid.setVerticalSpacing(10)

        self._checks: dict = {}
        formats = [
            ("html", "export", "HTML Dashboard",
             "Interactive, self-contained glass report with animated SVG charts", "#60a5fa"),
            ("md", "document", "Markdown Summary",
             "Executive Markdown with tables, insights and diagnostics", "#a78bfa"),
            ("json", "database", "JSON Data",
             "Full structured telemetry for programmatic use", "#22d3ee"),
            ("csv", "charts", "CSV Breakdown",
             "File-type table for Excel / PowerBI / Sheets", "#34d399"),
            ("txt", "files", "Plain Text",
             "Human-readable summary suitable for terminals / logs", "#cbd5e1"),
        ]
        for i, (key, icon, title, body, color) in enumerate(formats):
            card = QFrame()
            card.setObjectName("InsightCard")
            card.setProperty("severity", "info")
            lay = QHBoxLayout(card)
            lay.setContentsMargins(12, 10, 12, 10)
            lay.setSpacing(12)

            icon_lbl = QLabel()
            icon_lbl.setPixmap(get_svg_pixmap(icon, size=20, color=color))
            lay.addWidget(icon_lbl, 0, Qt.AlignTop)

            col = QVBoxLayout()
            col.setSpacing(2)
            t = QLabel(title)
            t.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: 700;")
            b = QLabel(body)
            b.setWordWrap(True)
            b.setStyleSheet("color: #94a3b8; font-size: 11px;")
            col.addWidget(t)
            col.addWidget(b)
            lay.addLayout(col, 1)

            cb = QCheckBox()
            cb.setChecked(True)
            self._checks[key] = cb
            lay.addWidget(cb, 0, Qt.AlignTop)

            formats_grid.addWidget(card, i // 2, i % 2)

        panel.body.addLayout(formats_grid)

        # Output directory row
        row = QHBoxLayout()
        row.setSpacing(10)
        self.dir_edit = QLineEdit()
        self.dir_edit.setPlaceholderText(
            "Output directory (defaults to 'folder_analysis' inside scanned folder)")
        browse = QPushButton("Browse")
        browse.setObjectName("BrowseButton")
        browse.setIcon(get_svg_icon("folder", color="#cbd5e1", size=16))
        browse.clicked.connect(self._browse)
        row.addWidget(self.dir_edit, 1)
        row.addWidget(browse)
        panel.body.addLayout(row)

        self.export_btn = QPushButton("  Generate & Export Reports")
        self.export_btn.setObjectName("RunButton")
        self.export_btn.setIcon(get_svg_icon("export", color="#ffffff", size=18))
        self.export_btn.setIconSize(QSize(18, 18))
        self.export_btn.setMinimumHeight(38)
        self.export_btn.clicked.connect(self._export)
        panel.body.addWidget(self.export_btn)

        root.addWidget(panel)

        # Status
        status_panel = Panel("Export Status", "check-circle",
                             "Output files and their sizes")
        self.status = QLabel(
            "Ready — run a scan and select formats to export.")
        self.status.setWordWrap(True)
        self.status.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.status.setStyleSheet(
            "color: #cbd5e1; font-size: 12px; line-height: 1.5;")
        status_panel.body.addWidget(self.status)

        btn_row = QHBoxLayout()
        self.open_dir_btn = QPushButton("  Open Output Folder")
        self.open_dir_btn.setObjectName("SecondaryButton")
        self.open_dir_btn.setIcon(get_svg_icon("external", color="#60a5fa", size=16))
        self.open_dir_btn.setVisible(False)
        self.open_dir_btn.clicked.connect(self._open_output_folder)
        btn_row.addWidget(self.open_dir_btn)
        btn_row.addStretch(1)
        status_panel.body.addLayout(btn_row)

        root.addWidget(status_panel)
        root.addStretch(1)

        self._last_exported_dir: str = ""

    def set_result(self, result: AnalysisResult) -> None:
        self.result = result
        if result.has_data:
            self.status.setText(
                f"Ready to export — {result.total_files:,} files indexed "
                f"({result.total_storage_formatted}).")
            self.export_badge.setText(
                f"{result.total_files:,} files")
        else:
            self.status.setText("Run a scan first.")
            self.export_badge.setText("no data")

    def _browse(self) -> None:
        start = self.dir_edit.text() or os.path.expanduser("~")
        chosen = QFileDialog.getExistingDirectory(self, "Choose output folder", start)
        if chosen:
            self.dir_edit.setText(chosen)

    def _open_output_folder(self) -> None:
        if self._last_exported_dir and os.path.isdir(self._last_exported_dir):
            import subprocess
            if os.name == "nt":
                os.startfile(self._last_exported_dir)
            else:
                subprocess.Popen(["xdg-open", self._last_exported_dir])

    def _export(self) -> None:
        if self.result is None or not self.result.has_data:
            self.status.setText("Nothing to export yet — run a scan first.")
            return
        chosen = [k for k, cb in self._checks.items() if cb.isChecked()]
        if not chosen:
            self.status.setText("Please select at least one format above.")
            return
        base = self.dir_edit.text().strip() or os.path.join(
            self.result.root_path, "folder_analysis")

        from folder_analyzer.exporters import (
            export_csv, export_html, export_json, export_markdown, export_txt)

        mapping = {
            "html": (export_html, "DASHBOARD.html", True),
            "md":   (export_markdown, "REPORT.md", True),
            "json": (export_json, "DATA.json", False),
            "csv":  (export_csv, "DATA.csv", False),
            "txt":  (export_txt, "SUMMARY.txt", False),
        }
        try:
            os.makedirs(base, exist_ok=True)
            self._last_exported_dir = base
            written = []
            for key in chosen:
                func, name, has_title = mapping[key]
                path = os.path.join(base, name)
                if has_title:
                    written.append(func(self.result, path,
                                        title=self.result.root_name))
                else:
                    written.append(func(self.result, path))

            lines = [f"Successfully exported {len(written)} report(s) to:"]
            lines.append(f"<b>{base}</b>")
            lines.append("")
            for p in written:
                lines.append(
                    f"  •  {os.path.basename(p)} "
                    f"<span style='color:#64748b'>({os.path.getsize(p):,} bytes)</span>")
            self.status.setText("<br/>".join(lines))
            self.open_dir_btn.setVisible(True)
            self.export_badge.setText(f"{len(written)} files")
        except Exception as exc:
            self.status.setText(f"Export failed: {exc}")
            self.open_dir_btn.setVisible(False)