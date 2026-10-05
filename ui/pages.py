"""Page widgets for the main window (all 9 pages)."""

from __future__ import annotations

import os
from typing import Any, Callable, Dict, List, Optional

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QSize, Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QFileDialog, QFrame, QGraphicsOpacityEffect,
    QGridLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QPushButton,
    QScrollArea, QSplitter, QTableWidget, QTableWidgetItem, QTabWidget,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from folder_analyzer.formats import format_size
from folder_analyzer.models import AnalysisResult
from .file_viewer import FileViewer
from .icons import get_category_svg_icon, get_svg_icon, get_svg_pixmap


# ===========================================================================
# Reusable components
# ===========================================================================

class StatCard(QFrame):
    def __init__(self, title: str, value: str = "—", subtitle: str = "",
                 icon_name: str = "activity", accent: str = "blue",
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("StatCard")
        self.setProperty("accent", accent)
        accent_color = {
            "cyan": "#00d2ff", "blue": "#4f8cff", "violet": "#8b5cf6",
            "green": "#22c55e", "amber": "#f59e0b", "red": "#ef4444",
        }.get(accent, "#4f8cff")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 14, 18, 14)
        outer.setSpacing(8)

        top = QHBoxLayout()
        top.setSpacing(10)
        self._icon_lbl = QLabel()
        self._icon_lbl.setFixedSize(28, 28)
        self._icon_lbl.setAlignment(Qt.AlignCenter)
        self._icon_lbl.setPixmap(get_svg_pixmap(icon_name, size=18, color=accent_color))
        self._icon_lbl.setStyleSheet(
            "background: rgba(255,255,255,0.05); border-radius: 8px; "
            "border: 1px solid rgba(255,255,255,0.06);")
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

        self._value = QLabel(value)
        self._value.setObjectName("StatCardValue")
        self._value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        outer.addWidget(self._value)

        self._sub = QLabel(subtitle)
        self._sub.setObjectName("StatCardSub")
        self._sub.setWordWrap(True)
        outer.addWidget(self._sub)
        outer.addStretch(1)

        self._effect = QGraphicsOpacityEffect(self)
        self._effect.setOpacity(1.0)
        self.setGraphicsEffect(self._effect)

    def set_value(self, value: str, subtitle: Optional[str] = None,
                  trend: Optional[str] = None) -> None:
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

    def set_badge(self, text: str) -> QLabel:
        badge = QLabel(text)
        badge.setObjectName("PanelBadge")
        self.header_actions.addWidget(badge)
        return badge


def make_table(headers: List[str]) -> QTableWidget:
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


# ===========================================================================
# Overview page
# ===========================================================================

class OverviewPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)

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
        self.action_text.setStyleSheet("color: #e2e8f0; font-size: 13px; font-weight: 500;")
        self.action_text.setWordWrap(True)
        act_lay.addWidget(self.action_text, 1)
        root.addWidget(self.action_box)

        panel = Panel("Storage Distribution by File Extension", "files",
                      "Ranked by aggregate size")
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
        fill_table(self.type_table, [])
        self.type_badge.setText("— extensions")

    def set_result(self, result: AnalysisResult) -> None:
        if not result.has_data:
            self._empty_state()
            return

        self.card_files.set_value(f"{result.total_files:,}",
                                  f"{result.empty_files_count} zero-byte file(s)")
        self.card_dirs.set_value(f"{result.total_directories:,}")
        self.card_size.set_value(result.total_storage_formatted)
        self.card_avg.set_value(result.avg_file_size_formatted)

        score = result.storage_efficiency_score
        trend = "↑ Healthy" if score >= 80 else "• Fair" if score >= 60 else "↓ Needs attention"
        self.card_health.set_value(f"{score}/100", result.storage_health_label, trend)
        self.card_dupes.set_value(
            result.duplicate_wasted_formatted if result.duplicate_groups else "0 B",
            f"{len(result.duplicate_groups)} duplicate cluster(s)")

        if result.actionable_recommendations:
            top = result.actionable_recommendations[0]
            self.action_text.setText(
                f"<b>Recommendation ({top['type']}):</b> {top['title']} — {top['action']}")
        else:
            self.action_text.setText(
                "<b>Optimal Layout:</b> Directory storage is well organized with "
                "no detected duplicate waste.")

        rows = []
        for d in result.file_types:
            icon = get_category_svg_icon(d["category"], size=16)
            item_ext = QTableWidgetItem(icon, "  " + d["label"])
            rows.append([item_ext, d["category"], f"{d['files']:,}",
                         d["size_formatted"], f"{d['percentage']}%"])
        fill_table(self.type_table, rows)
        self.type_badge.setText(f"{len(result.file_types)} extensions")


# ===========================================================================
# Charts / Timeline helpers
# ===========================================================================

def _donut(entries, value_key="size", label_key="label", max_slices=8):
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


def _bars(entries, value_key="size", label_key="name", color="#4f8cff"):
    from PySide6.QtGui import QColor
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


# ===========================================================================
# Charts page
# ===========================================================================

class ChartsPage(QWidget):
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
        self._view_timeline = _view()

        p1 = Panel("Storage by File Type", "files", "Top 8 extensions")
        p1.body.addWidget(self._view_type)
        p2 = Panel("Storage by Category", "layers", "Grouped by media class")
        p2.body.addWidget(self._view_cat)
        p3 = Panel("Top Directories", "folder", "Highest aggregate footprint")
        p3.body.addWidget(self._view_dirs)
        p4 = Panel("File Age Distribution", "clock", "Recency buckets")
        p4.body.addWidget(self._view_age)
        p5 = Panel("File Size Distribution", "activity", "Size class breakdown")
        p5.body.addWidget(self._view_size)
        p6 = Panel("Modified Timeline", "calendar", "Files by month (last 24)")
        p6.body.addWidget(self._view_timeline)

        root.addWidget(p1, 0, 0)
        root.addWidget(p2, 0, 1)
        root.addWidget(p3, 1, 0, 1, 2)
        root.addWidget(p4, 2, 0)
        root.addWidget(p5, 2, 1)
        root.addWidget(p6, 3, 0, 1, 2)
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
        self._view_timeline.setChart(
            _bars(result.modified_timeline, "size", "month", "#8b5cf6"))


# ===========================================================================
# Files page
# ===========================================================================

class FilesPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._viewer_callback: Optional[Callable[[str], None]] = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        panel = Panel("File Explorer", "files",
                      "Double-click a row to preview it in the File Viewer")
        self.file_badge = panel.set_badge("0 files")

        tabs = QTabWidget()
        self.table_largest = make_table(["Name", "Location", "Type", "Size", "Modified"])
        self.table_oldest = make_table(["Name", "Location", "Type", "Size", "Modified"])
        self.table_recent = make_table(["Name", "Location", "Type", "Size", "Modified"])
        self.table_empty = make_table(["Name", "Location", "Type", "Size", "Modified"])

        for name, table in (("Largest", self.table_largest),
                            ("Oldest", self.table_oldest),
                            ("Recent", self.table_recent),
                            ("0-Byte", self.table_empty)):
            wrap = QWidget()
            wl = QVBoxLayout(wrap)
            wl.setContentsMargins(0, 6, 0, 0)
            wl.setSpacing(8)
            wl.addWidget(FilterBar(table))
            wl.addWidget(table, 1)
            tabs.addTab(wrap, name)
            table.itemDoubleClicked.connect(self._on_item_double_click)

        panel.body.addWidget(tabs, 1)
        root.addWidget(panel, 1)

    def set_viewer_callback(self, cb: Callable[[str], None]) -> None:
        self._viewer_callback = cb

    def _on_item_double_click(self, item: QTableWidgetItem) -> None:
        if self._viewer_callback is None:
            return
        table = item.tableWidget()
        name_item = table.item(item.row(), 0)
        if name_item is None:
            return
        path = name_item.data(Qt.UserRole)
        if path:
            self._viewer_callback(path)

    def set_result(self, result: AnalysisResult) -> None:
        def build(records):
            out = []
            for r in records:
                cat = r.get("type", "Other") if isinstance(r, dict) else r.type
                name = r.get("name", "") if isinstance(r, dict) else r.name
                parent = r.get("parent", "") if isinstance(r, dict) else r.parent
                size_str = r.get("size_formatted", "") if isinstance(r, dict) else r.size_formatted
                mod_str = r.get("modified_formatted", "") if isinstance(r, dict) else r.modified_formatted
                path = r.get("path", "") if isinstance(r, dict) else getattr(r, "path", "")
                icon = get_category_svg_icon(cat, size=16)
                name_item = QTableWidgetItem(icon, "  " + name)
                if path:
                    name_item.setData(Qt.UserRole, path)
                out.append([name_item, parent, cat, size_str, mod_str])
            return out

        fill_table(self.table_largest, build(result.largest_files))
        fill_table(self.table_oldest, build(result.oldest_files))
        fill_table(self.table_recent, build(getattr(result, "recent_files", [])))
        fill_table(self.table_empty, build(result.empty_files_list))
        total = (len(result.largest_files) + len(result.oldest_files) +
                 len(getattr(result, "recent_files", [])) + len(result.empty_files_list))
        self.file_badge.setText(f"{total} rows")


# ===========================================================================
# File Viewer page
# ===========================================================================

class FileViewerPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._result: AnalysisResult | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        panel = Panel("File Viewer", "files",
                      "Browse files from the scan and preview them in-app")
        self.viewer_badge = panel.set_badge("no scan")

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(8)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Filter files by name…")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._apply_filter)
        ll.addWidget(self.search)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["File", "Size"])
        self.tree.setColumnWidth(0, 240)
        self.tree.setAlternatingRowColors(True)
        self.tree.setUniformRowHeights(True)
        self.tree.itemSelectionChanged.connect(self._on_tree_selection)
        ll.addWidget(self.tree, 1)
        splitter.addWidget(left)

        self.viewer = FileViewer()
        splitter.addWidget(self.viewer)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([320, 900])

        panel.body.addWidget(splitter, 1)
        root.addWidget(panel, 1)

    def open_path(self, path: str) -> None:
        self.viewer.load_file(path)
        self._select_path_in_tree(path)

    def set_result(self, result: AnalysisResult) -> None:
        self._result = result
        self._rebuild_tree(result)
        self.viewer_badge.setText(f"{result.total_files:,} files")

    def _rebuild_tree(self, result: AnalysisResult) -> None:
        self.tree.clear()
        if not result.has_data:
            return
        root_path = result.root_path
        root_item = QTreeWidgetItem([result.root_name + "/", ""])
        root_item.setIcon(0, get_svg_icon("folder", color="#93c5fd", size=16))
        self.tree.addTopLevelItem(root_item)

        by_parent: Dict[str, List[Dict]] = {}
        for rec in (result.largest_files + result.oldest_files
                    + getattr(result, "recent_files", []) + result.empty_files_list):
            parent = rec.get("parent_full") or rec.get("path", "")
            by_parent.setdefault(parent, []).append(rec)

        for parent_path, recs in sorted(by_parent.items()):
            if not parent_path:
                continue
            try:
                short = os.path.relpath(parent_path, root_path)
            except ValueError:
                short = parent_path
            dir_item = QTreeWidgetItem([short, ""])
            dir_item.setIcon(0, get_svg_icon("folder", color="#c4b5fd", size=16))
            root_item.addChild(dir_item)
            for rec in recs:
                file_item = QTreeWidgetItem(
                    [rec.get("name", "?"), rec.get("size_formatted", "")])
                file_item.setIcon(0, get_category_svg_icon(rec.get("type", "Other"), size=14))
                file_item.setData(0, Qt.UserRole, rec.get("path", ""))
                dir_item.addChild(file_item)
        root_item.setExpanded(True)

    def _apply_filter(self, text: str) -> None:
        needle = text.lower().strip()

        def visit(item: QTreeWidgetItem) -> bool:
            if not needle:
                item.setHidden(False)
                for i in range(item.childCount()):
                    visit(item.child(i))
                return True
            match = needle in item.text(0).lower()
            child_match = False
            for i in range(item.childCount()):
                if visit(item.child(i)):
                    child_match = True
            show = match or child_match
            item.setHidden(not show)
            if child_match:
                item.setExpanded(True)
            return show

        for i in range(self.tree.topLevelItemCount()):
            visit(self.tree.topLevelItem(i))

    def _on_tree_selection(self) -> None:
        items = self.tree.selectedItems()
        if not items:
            return
        path = items[0].data(0, Qt.UserRole)
        if path:
            self.viewer.load_file(path)

    def _select_path_in_tree(self, path: str) -> None:
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            found = self._find_child_by_path(top, path)
            if found:
                self.tree.setCurrentItem(found)
                self.tree.scrollToItem(found)
                return

    def _find_child_by_path(self, item: QTreeWidgetItem,
                            path: str) -> Optional[QTreeWidgetItem]:
        if item.data(0, Qt.UserRole) == path:
            return item
        for i in range(item.childCount()):
            found = self._find_child_by_path(item.child(i), path)
            if found:
                item.setExpanded(True)
                return found
        return None


# ===========================================================================
# Timeline page
# ===========================================================================

class TimelinePage(QWidget):
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

        root = QVBoxLayout(inner)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)

        def _view():
            v = QChartView()
            v.setRenderHint(QPainter.RenderHint.Antialiasing)
            v.setMinimumHeight(240)
            return v

        self._view_month = _view()
        self._view_dow = _view()
        self._view_hour = _view()

        p1 = Panel("Files Modified per Month", "calendar",
                   "Storage weight by month (last 24)")
        p1.body.addWidget(self._view_month)
        p2 = Panel("Files Modified per Weekday", "clock",
                   "Aggregate storage by day of week")
        p2.body.addWidget(self._view_dow)
        p3 = Panel("Files Modified per Hour", "activity",
                   "Storage weight by hour of day")
        p3.body.addWidget(self._view_hour)

        root.addWidget(p1)
        root.addWidget(p2)
        root.addWidget(p3)

    def set_result(self, result: AnalysisResult) -> None:
        self._view_month.setChart(
            _bars(result.modified_timeline, "size", "month", "#8b5cf6"))
        self._view_dow.setChart(
            _bars(result.day_of_week_distribution, "size", "day", "#06b6d4"))
        self._view_hour.setChart(
            _bars(result.hour_of_day_distribution, "size", "hour", "#a855f7"))


# ===========================================================================
# Advanced page
# ===========================================================================

class AdvancedPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._viewer_callback: Optional[Callable[[str], None]] = None

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

        kpi = QHBoxLayout()
        kpi.setSpacing(12)
        self.card_junk = StatCard("Junk Candidates", "—", "Temp / cache files",
                                  icon_name="trash", accent="red")
        self.card_name_dupes = StatCard("Filename Collisions", "—",
                                        "Same name, diff folder",
                                        icon_name="copy", accent="amber")
        self.card_deep = StatCard("Deep Files", "—", "Nested > threshold",
                                  icon_name="layers", accent="violet")
        self.card_long = StatCard("Long Paths", "—", "> 240 chars",
                                  icon_name="alert-circle", accent="amber")
        for c in (self.card_junk, self.card_name_dupes, self.card_deep, self.card_long):
            kpi.addWidget(c, 1)
        root.addLayout(kpi)

        p1 = Panel("Filename Collisions", "copy",
                   "Same filename found in multiple directories")
        self.dup_badge = p1.set_badge("0")
        self.dup_table = make_table(["Filename", "Copies", "Total Size", "Example Path"])
        p1.body.addWidget(FilterBar(self.dup_table))
        p1.body.addWidget(self.dup_table, 1)
        self._wire_viewer(self.dup_table)
        root.addWidget(p1)

        p2 = Panel("Junk / Temp / Cache Candidates", "trash",
                   "Old temporary or backup files safe to review")
        self.junk_badge = p2.set_badge("0")
        self.junk_table = make_table(["Name", "Location", "Type", "Size", "Age (days)"])
        p2.body.addWidget(FilterBar(self.junk_table))
        p2.body.addWidget(self.junk_table, 1)
        self._wire_viewer(self.junk_table)
        root.addWidget(p2)

        two = QHBoxLayout()
        two.setSpacing(14)

        p3 = Panel("Deeply Nested Files", "layers", "Beyond the depth threshold")
        self.deep_badge = p3.set_badge("0")
        self.deep_table = make_table(["Name", "Location", "Depth", "Size"])
        p3.body.addWidget(FilterBar(self.deep_table))
        p3.body.addWidget(self.deep_table, 1)
        two.addWidget(p3)

        p4 = Panel("Long Paths", "alert-circle", "Paths exceeding safe limits")
        self.long_badge = p4.set_badge("0")
        self.long_table = make_table(["Name", "Path Length", "Location"])
        p4.body.addWidget(FilterBar(self.long_table))
        p4.body.addWidget(self.long_table, 1)
        two.addWidget(p4)
        root.addLayout(two)

        two2 = QHBoxLayout()
        two2.setSpacing(14)

        p5 = Panel("Rough MIME Summary", "database",
                   "Distribution by top-level media type")
        self.mime_table = make_table(["MIME", "Files", "Size", "% Share"])
        p5.body.addWidget(self.mime_table, 1)
        two2.addWidget(p5)

        p6 = Panel("Files Without Extension", "files",
                   "Scripts, configs or unknown binaries")
        self.extless_badge = p6.set_badge("0")
        self.extless_table = make_table(["Name", "Location", "Size"])
        p6.body.addWidget(FilterBar(self.extless_table))
        p6.body.addWidget(self.extless_table, 1)
        two2.addWidget(p6)
        root.addLayout(two2)

    def set_viewer_callback(self, cb: Callable[[str], None]) -> None:
        self._viewer_callback = cb

    def _wire_viewer(self, table: QTableWidget) -> None:
        def on_dc(item: QTableWidgetItem) -> None:
            if self._viewer_callback is None:
                return
            name_item = table.item(item.row(), 0)
            if name_item is None:
                return
            path = name_item.data(Qt.UserRole)
            if path:
                self._viewer_callback(path)
        table.itemDoubleClicked.connect(on_dc)

    def set_result(self, result: AnalysisResult) -> None:
        junk_size = sum(j["size"] for j in result.potential_junk)
        self.card_junk.set_value(f"{len(result.potential_junk):,}",
                                 f"{format_size(junk_size)} recoverable")
        self.card_name_dupes.set_value(f"{len(result.filename_duplicates):,}")
        self.card_deep.set_value(f"{len(result.deep_files):,}")
        self.card_long.set_value(f"{len(result.long_path_files):,}")

        rows = []
        for d in result.filename_duplicates[:200]:
            example = d["files"][0]["parent"] if d.get("files") else ""
            name_item = QTableWidgetItem(d["name"])
            if d.get("files"):
                name_item.setData(Qt.UserRole, d["files"][0].get("path", ""))
            rows.append([name_item, f"{d['count']}", d["size_formatted"], example])
        fill_table(self.dup_table, rows)
        self.dup_badge.setText(f"{len(result.filename_duplicates)}")

        rows = []
        for j in result.potential_junk:
            name_item = QTableWidgetItem(j["name"])
            name_item.setData(Qt.UserRole, j.get("path", ""))
            rows.append([name_item, j.get("parent", ""), j.get("type", "Other"),
                         j["size_formatted"], f"{j.get('age_days', 0):,}"])
        fill_table(self.junk_table, rows)
        self.junk_badge.setText(f"{len(result.potential_junk)}")

        rows = []
        for d in result.deep_files:
            name_item = QTableWidgetItem(d["name"])
            name_item.setData(Qt.UserRole, d.get("path", ""))
            rows.append([name_item, d.get("parent", ""),
                         f"{d.get('depth', 0)}", d["size_formatted"]])
        fill_table(self.deep_table, rows)
        self.deep_badge.setText(f"{len(result.deep_files)}")

        rows = [[d["name"], f"{d.get('path_len', 0)}", d.get("parent", "")]
                for d in result.long_path_files]
        fill_table(self.long_table, rows)
        self.long_badge.setText(f"{len(result.long_path_files)}")

        rows = [[m["mime"], f"{m['files']:,}", m["size_formatted"],
                 f"{m['percentage']}%"] for m in result.mime_summary]
        fill_table(self.mime_table, rows)

        rows = []
        for e in result.extensionless_files:
            name_item = QTableWidgetItem(e["name"])
            name_item.setData(Qt.UserRole, e.get("path", ""))
            rows.append([name_item, e.get("parent", ""), e["size_formatted"]])
        fill_table(self.extless_table, rows)
        self.extless_badge.setText(f"{len(result.extensionless_files)}")


# ===========================================================================
# Duplicates page
# ===========================================================================

class DuplicatesPage(QWidget):
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
            f"keeping one copy of each group.")
        self.dup_badge.setText(f"{len(result.duplicate_groups)} groups")

        group_icon = get_svg_icon("duplicates", color="#f87171", size=16)
        for group in result.duplicate_groups:
            top = QTreeWidgetItem([
                f"{group['count']} copies · {group['size_formatted']} each",
                f"Wasted space: {group['wasted_formatted']}", "", ""])
            top.setIcon(0, group_icon)
            top.setFirstColumnSpanned(True)
            self.tree.addTopLevelItem(top)
            for f in group["files"]:
                child = QTreeWidgetItem([
                    "  " + f["name"], f["parent"],
                    f["size_formatted"], f["modified_formatted"]])
                child.setIcon(0, get_category_svg_icon(f.get("type", "Other"), size=16))
                top.addChild(child)
        self.tree.expandToDepth(0)


# ===========================================================================
# Insights page
# ===========================================================================

class InsightsPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)

        panel_rec = Panel("Actionable Optimization Recommendations", "sparkles",
                          "Ranked by impact on storage footprint")
        self.rec_container = QVBoxLayout()
        self.rec_container.setSpacing(8)
        panel_rec.body.addLayout(self.rec_container)
        root.addWidget(panel_rec, 3)

        panel_ins = Panel("Key Insights & Storage Telemetry", "insights",
                          "Automatic observations from the analysis")
        self.insights_container = QVBoxLayout()
        self.insights_container.setSpacing(6)
        panel_ins.body.addLayout(self.insights_container)
        root.addWidget(panel_ins, 3)

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

        self._clear_layout(self.insights_container)
        for ins in result.key_insights:
            self.insights_container.addWidget(
                self._make_insight_card(
                    "info", "check-circle", "#60a5fa", ins.replace("**", "")))

        self.tree_view.setText(result.tree_text or "—")
        self.warnings.setText(
            "  ⚠  " + "  ·  ".join(result.warnings) if result.warnings else "")


# ===========================================================================
# Export page
# ===========================================================================

class ExportPage(QWidget):
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
            "Reports include a self-contained glassmorphic dashboard, structured "
            "telemetry, and executive summaries suitable for sharing.")
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

        status_panel = Panel("Export Status", "check-circle",
                             "Output files and their sizes")
        self.status = QLabel("Ready — run a scan and select formats to export.")
        self.status.setWordWrap(True)
        self.status.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.status.setStyleSheet("color: #cbd5e1; font-size: 12px; line-height: 1.5;")
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
            self.export_badge.setText(f"{result.total_files:,} files")
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
                    written.append(func(self.result, path, title=self.result.root_name))
                else:
                    written.append(func(self.result, path))

            lines = [f"Successfully exported {len(written)} report(s) to:",
                     f"<b>{base}</b>", ""]
            for p in written:
                lines.append(f"  •  {os.path.basename(p)} "
                             f"<span style='color:#64748b'>({os.path.getsize(p):,} bytes)</span>")
            self.status.setText("<br/>".join(lines))
            self.open_dir_btn.setVisible(True)
            self.export_badge.setText(f"{len(written)} files")
        except Exception as exc:
            self.status.setText(f"Export failed: {exc}")
            self.open_dir_btn.setVisible(False)