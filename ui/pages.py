"""
Page widgets for the main window with glassmorphism aesthetics, SVG vector icons,
comprehensive deep storage insights, health analytics, and smooth transitions.

Every page exposes ``set_result(result)`` so the main window can push a
fresh :class:`AnalysisResult` into it after each scan.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import (
    QEasingCurve, QPropertyAnimation, Qt,
)
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QCheckBox, QFileDialog, QFrame, QGraphicsOpacityEffect, QGridLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QPushButton, QTableWidget, QTableWidgetItem, QTabWidget, QTreeWidget,
    QTreeWidgetItem, QVBoxLayout, QWidget,
)

from folder_analyzer.models import AnalysisResult
from .icons import get_category_svg_icon, get_svg_icon, get_svg_pixmap


# ---------------------------------------------------------------------------
# Small reusable animated glass widgets
# ---------------------------------------------------------------------------

class StatCard(QFrame):
    """A rounded glass card with gradient accent, animated opacity pulse and SVG icon."""

    def __init__(self, title: str, value: str = "—", subtitle: str = "",
                 icon_name: str = "", accent_color: str = "#4f8cff",
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("StatCard")
        self._accent_color = accent_color

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(6)

        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        if icon_name:
            self._icon_lbl = QLabel()
            self._icon_lbl.setPixmap(get_svg_pixmap(icon_name, size=18, color=accent_color))
            header_row.addWidget(self._icon_lbl)
        else:
            self._icon_lbl = None

        self._title = QLabel(title.upper())
        self._title.setObjectName("StatCardTitle")
        header_row.addWidget(self._title)
        header_row.addStretch(1)
        layout.addLayout(header_row)

        self._value = QLabel(value)
        self._value.setObjectName("StatCardValue")
        self._value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self._value)

        if subtitle:
            self._sub = QLabel(subtitle)
            self._sub.setObjectName("StatCardSub")
            layout.addWidget(self._sub)
        else:
            self._sub = None

        layout.addStretch(1)

        # Pulse animation on update
        self._effect = QGraphicsOpacityEffect(self)
        self._effect.setOpacity(1.0)
        self.setGraphicsEffect(self._effect)

    def set_value(self, value: str, subtitle: Optional[str] = None) -> None:
        self._value.setText(value)
        if subtitle is not None and self._sub is not None:
            self._sub.setText(subtitle)
        self.trigger_pulse_animation()

    def trigger_pulse_animation(self) -> None:
        """Play a smooth opacity fade pulse when numbers change."""
        self._anim = QPropertyAnimation(self._effect, b"opacity")
        self._anim.setDuration(300)
        self._anim.setStartValue(0.4)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.start()


def make_table(headers: List[str], stretch_first: bool = True) -> QTableWidget:
    """Create a read-only glassmorphic table."""
    table = QTableWidget(0, len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.verticalHeader().setVisible(False)
    table.setAlternatingRowColors(True)
    table.setEditTriggers(QTableWidget.NoEditTriggers)
    table.setSelectionBehavior(QTableWidget.SelectRows)
    table.setWordWrap(False)
    table.setShowGrid(False)
    if stretch_first:
        table.horizontalHeader().setStretchLastSection(False)
    return table


def fill_table(table: QTableWidget, rows: List[List[Any]]) -> None:
    """Replace the contents of a table with ``rows``."""
    table.setRowCount(0)
    for row in rows:
        index = table.rowCount()
        table.insertRow(index)
        for col, val in enumerate(row):
            if isinstance(val, QTableWidgetItem):
                item = val
            else:
                item = QTableWidgetItem(str(val))
                if col > 0 and any(char.isdigit() for char in str(val)):
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            table.setItem(index, col, item)
    if table.rowCount():
        table.resizeColumnsToContents()
        table.setColumnWidth(0, max(table.columnWidth(0), 190))


def _panel(title: str, icon_name: str = "") -> tuple:
    """Create a titled glass panel (QGroupBox) with a vertical layout and optional SVG icon."""
    box = QGroupBox(title)
    layout = QVBoxLayout(box)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(10)
    return box, layout


# ---------------------------------------------------------------------------
# Overview page
# ---------------------------------------------------------------------------

class OverviewPage(QWidget):
    """Headline metrics + storage health + actionable recommendations + file types."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)

        # 6 Stat cards in grid or row
        cards = QHBoxLayout()
        cards.setSpacing(12)
        self.card_files = StatCard("Files", "—", "Total indexed items", icon_name="files", accent_color="#38bdf8")
        self.card_dirs = StatCard("Folders", "—", "Directory branches", icon_name="folder", accent_color="#818cf8")
        self.card_size = StatCard("Storage", "—", "Total disk space", icon_name="overview", accent_color="#34d399")
        self.card_avg = StatCard("Avg Size", "—", "Calculated mean", icon_name="charts", accent_color="#a78bfa")
        self.card_health = StatCard("Health Score", "—", "Storage efficiency", icon_name="health", accent_color="#22c55e")
        self.card_dupes = StatCard("Duplicate Waste", "—", "Potential recovery", icon_name="duplicates", accent_color="#f87171")
        for card in (self.card_files, self.card_dirs, self.card_size,
                     self.card_avg, self.card_health, self.card_dupes):
            cards.addWidget(card, 1)
        root.addLayout(cards)

        # Actionable Optimization Banner
        self.action_box = QFrame()
        self.action_box.setStyleSheet(
            "background: rgba(30, 41, 59, 0.7); border: 1px solid rgba(96, 165, 250, 0.3); "
            "border-radius: 12px; padding: 12px 16px;"
        )
        act_lay = QHBoxLayout(self.action_box)
        act_lay.setContentsMargins(12, 8, 12, 8)
        act_lay.setSpacing(12)

        self.action_icon = QLabel()
        self.action_icon.setPixmap(get_svg_pixmap("sparkles", size=24, color="#38bdf8"))
        act_lay.addWidget(self.action_icon)

        self.action_text = QLabel("Run an analysis on any folder to view immediate storage recovery tips.")
        self.action_text.setStyleSheet("color: #e2e8f0; font-size: 13px; font-weight: 500;")
        self.action_text.setWordWrap(True)
        act_lay.addWidget(self.action_text, 1)
        root.addWidget(self.action_box)

        # Type table
        panel, layout = _panel("Storage Distribution by File Extension", icon_name="files")
        self.type_table = make_table(["Extension", "Category", "Files", "Size", "% of storage"])
        layout.addWidget(self.type_table)
        root.addWidget(panel, 1)

        self._empty_state()

    def _empty_state(self) -> None:
        self.card_files.set_value("—")
        self.card_dirs.set_value("—")
        self.card_size.set_value("—")
        self.card_avg.set_value("—")
        self.card_health.set_value("—", "Storage efficiency")
        self.card_dupes.set_value("—", "Potential recovery")
        self.action_text.setText("Run an analysis on any folder to view immediate storage recovery tips.")
        fill_table(self.type_table, [])

    def set_result(self, result: AnalysisResult) -> None:
        if not result.has_data:
            self._empty_state()
            return
        self.card_files.set_value(f"{result.total_files:,}", f"{result.empty_files_count} zero-byte files")
        self.card_dirs.set_value(f"{result.total_directories:,}")
        self.card_size.set_value(result.total_storage_formatted)
        self.card_avg.set_value(result.avg_file_size_formatted)
        self.card_health.set_value(f"{result.storage_efficiency_score}/100", result.storage_health_label)
        self.card_dupes.set_value(
            result.duplicate_wasted_formatted if result.duplicate_groups else "0 B",
            f"{len(result.duplicate_groups)} duplicate clusters"
        )

        if result.actionable_recommendations:
            top_rec = result.actionable_recommendations[0]
            self.action_text.setText(f"💡 <b>Recommendation ({top_rec['type']}):</b> {top_rec['title']} — {top_rec['action']}")
        else:
            self.action_text.setText(f"✨ <b>Optimal Layout:</b> Directory storage is well organized with no detected duplicate waste.")

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


# ---------------------------------------------------------------------------
# Charts page (QtCharts with animation enabled)
# ---------------------------------------------------------------------------

def _donut(entries: List[Dict[str, Any]], value_key: str = "size",
           label_key: str = "label", max_slices: int = 8):
    """Build an animated dark glass donut chart from aggregate rows."""
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
    series.setHoleSize(0.48)
    for d in rows:
        val = float(d.get(value_key, 0))
        slice_ = series.append(str(d.get(label_key, "?")), val)
        slice_.setBrush(QColor(d.get("color", "#4f8cff")))
        slice_.setLabelVisible(total > 0 and val / total >= 0.05)
        slice_.setLabelColor(QColor("#f8fafc"))

    chart = QChart()
    chart.setTheme(QChart.ChartTheme.ChartThemeDark)
    chart.setAnimationOptions(QChart.AnimationOption.AllAnimations)
    chart.setAnimationDuration(600)
    chart.setAnimationEasingCurve(QEasingCurve.OutCubic)
    chart.addSeries(series)
    chart.legend().setVisible(True)
    chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)
    chart.setBackgroundVisible(False)
    chart.setMargins(QMargins(6, 6, 6, 6))
    return chart


def _bars(entries: List[Dict[str, Any]], value_key: str = "size",
          label_key: str = "name", color: str = "#4f8cff"):
    """Build an animated dark horizontal bar chart from aggregate rows."""
    from PySide6.QtGui import QColor
    from PySide6.QtCharts import QBarCategoryAxis, QBarSeries, QBarSet, QChart, QValueAxis

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
    axis_y = QValueAxis()
    axis_y.setLabelFormat("%.0f")
    max_v = max(values) if values else 1.0
    axis_y.setRange(0, max_v * 1.15 if max_v else 1)

    chart = QChart()
    chart.setTheme(QChart.ChartTheme.ChartThemeDark)
    chart.setAnimationOptions(QChart.AnimationOption.AllAnimations)
    chart.setAnimationDuration(600)
    chart.setAnimationEasingCurve(QEasingCurve.OutCubic)
    chart.addSeries(series)
    chart.setAxisX(axis_x, series)
    chart.setAxisY(axis_y, series)
    chart.legend().setVisible(False)
    chart.setBackgroundVisible(False)
    return chart


class ChartsPage(QWidget):
    """Live visual analytics: types, categories, directory hotspots, age & size distribution."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        from PySide6.QtCharts import QChartView
        from PySide6.QtGui import QPainter

        root = QGridLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)

        self._view_type = QChartView()
        self._view_cat = QChartView()
        self._view_dirs = QChartView()
        self._view_age = QChartView()
        self._view_size = QChartView()
        for view in (self._view_type, self._view_cat, self._view_dirs,
                     self._view_age, self._view_size):
            view.setRenderHint(QPainter.RenderHint.Antialiasing)

        panel_type, lay_type = _panel("Storage by File Type")
        lay_type.addWidget(self._view_type)
        panel_cat, lay_cat = _panel("Storage by Category")
        lay_cat.addWidget(self._view_cat)
        panel_dirs, lay_dirs = _panel("Top Directories (Largest Footprint)")
        lay_dirs.addWidget(self._view_dirs)
        panel_age, lay_age = _panel("File Age Distribution (Recency)")
        lay_age.addWidget(self._view_age)
        panel_size, lay_size = _panel("File Size Distribution (Scale)")
        lay_size.addWidget(self._view_size)

        root.addWidget(panel_type, 0, 0)
        root.addWidget(panel_cat, 0, 1)
        root.addWidget(panel_dirs, 1, 0, 1, 2)
        root.addWidget(panel_age, 2, 0)
        root.addWidget(panel_size, 2, 1)
        root.setRowStretch(0, 3)
        root.setRowStretch(1, 3)
        root.setRowStretch(2, 3)
        root.setColumnStretch(0, 1)
        root.setColumnStretch(1, 1)

    def set_result(self, result: AnalysisResult) -> None:
        self._view_type.setChart(_donut(result.file_types, "size", "label", 8))
        self._view_cat.setChart(_donut(result.categories, "size", "name", 9))
        self._view_dirs.setChart(_bars(result.top_directories[:10], "size", "name", "#3b82f6"))
        self._view_age.setChart(_bars(result.age_distribution, "size", "category", "#06b6d4"))
        self._view_size.setChart(
            _bars(result.size_distribution, "count", "range", "#a855f7"))


# ---------------------------------------------------------------------------
# Files page
# ---------------------------------------------------------------------------

class FilesPage(QWidget):
    """Largest files, oldest files, and 0-byte orphan files in tabbed glass tables."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        tabs = QTabWidget()
        self.table_largest = make_table(["Name", "Location", "Type", "Size", "Modified"])
        self.table_oldest = make_table(["Name", "Location", "Type", "Size", "Modified"])
        self.table_empty = make_table(["Name", "Location", "Type", "Size", "Modified"])

        tabs.addTab(self.table_largest, "Largest files")
        tabs.addTab(self.table_oldest, "Oldest files")
        tabs.addTab(self.table_empty, "0-Byte Empty files")
        root.addWidget(tabs)

    def set_result(self, result: AnalysisResult) -> None:
        def build_rows(records):
            output = []
            for r in records:
                cat = r.get("type", "Other") if isinstance(r, dict) else r.type
                name = r.get("name", "") if isinstance(r, dict) else r.name
                parent = r.get("parent", "") if isinstance(r, dict) else r.parent
                size_str = r.get("size_formatted", "") if isinstance(r, dict) else r.size_formatted
                mod_str = r.get("modified_formatted", "") if isinstance(r, dict) else r.modified_formatted

                icon = get_category_svg_icon(cat, size=16)
                name_item = QTableWidgetItem(icon, "  " + name)
                output.append([name_item, parent, cat, size_str, mod_str])
            return output

        fill_table(self.table_largest, build_rows(result.largest_files))
        fill_table(self.table_oldest, build_rows(result.oldest_files))
        fill_table(self.table_empty, build_rows(result.empty_files_list))


# ---------------------------------------------------------------------------
# Duplicates page
# ---------------------------------------------------------------------------

class DuplicatesPage(QWidget):
    """Duplicate groups with wasted-space summary using SVG vector icons."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)

        panel, layout = _panel("Duplicate Storage Detection & Recovery", icon_name="duplicates")
        self.summary = QLabel("No duplicate detection has been run yet.")
        self.summary.setWordWrap(True)
        self.summary.setStyleSheet("color: #94a3b8; font-size: 13px; font-weight: 500;")
        layout.addWidget(self.summary)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["File / Redundant Copy", "Location", "Size", "Modified"])
        self.tree.setAlternatingRowColors(True)
        self.tree.setWordWrap(False)
        self.tree.setRootIsDecorated(True)
        layout.addWidget(self.tree, 1)

        root.addWidget(panel, 1)

    def set_result(self, result: AnalysisResult) -> None:
        self.tree.clear()
        if not result.duplicate_groups:
            self.summary.setText("No duplicate files were found in this directory.")
            return
        self.summary.setText(
            f"Found {len(result.duplicate_groups)} duplicate group(s) — "
            f"approximately {result.duplicate_wasted_formatted} could be recovered "
            f"by keeping one copy of each group."
        )
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


# ---------------------------------------------------------------------------
# Insights page
# ---------------------------------------------------------------------------

class InsightsPage(QWidget):
    """Storage health, actionable optimization recommendations, key insights & hierarchy tree."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)

        # Optimization recommendations panel
        panel_rec, lay_rec = _panel("Actionable Optimization Recommendations", icon_name="sparkles")
        self.rec_list = QListWidget()
        self.rec_list.setStyleSheet(
            "border: none; background: transparent; font-size: 13px; line-height: 1.5;"
        )
        lay_rec.addWidget(self.rec_list)
        root.addWidget(panel_rec, 2)

        # Observations & Diagnostics
        panel_ins, lay_ins = _panel("Key Insights & Storage Telemetry", icon_name="insights")
        self.insights = QListWidget()
        self.insights.setStyleSheet("border: none; background: transparent; padding: 4px;")
        lay_ins.addWidget(self.insights)
        root.addWidget(panel_ins, 2)

        # Directory tree preview
        panel2, layout2 = _panel("Directory Hierarchy Tree (Top Level)", icon_name="folder")
        self.tree_view = QLabel()
        self.tree_view.setTextFormat(Qt.PlainText)
        self.tree_view.setWordWrap(False)
        self.tree_view.setStyleSheet(
            "font-family: 'SFMono-Regular', Consolas, 'Courier New', monospace;"
            "font-size: 12px; color: #93c5fd; padding: 12px; "
            "background: rgba(10, 15, 26, 0.85); border-radius: 8px;")
        layout2.addWidget(self.tree_view)
        root.addWidget(panel2, 2)

        self.warnings = QLabel()
        self.warnings.setWordWrap(True)
        self.warnings.setStyleSheet("color: #f87171; font-size: 12px; font-weight: 600; padding: 4px;")
        root.addWidget(self.warnings)

    def set_result(self, result: AnalysisResult) -> None:
        # Recommendations
        self.rec_list.clear()
        rec_icon = get_svg_icon("sparkles", color="#38bdf8", size=16)
        crit_icon = get_svg_icon("warning", color="#ef4444", size=16)
        if result.actionable_recommendations:
            for rec in result.actionable_recommendations:
                item = QListWidgetItem(f"[{rec['type']}] {rec['title']} — {rec['action']}")
                item.setIcon(crit_icon if rec["type"] == "Critical" else rec_icon)
                self.rec_list.addItem(item)
        else:
            item = QListWidgetItem("No storage warnings. Everything is in optimal condition.")
            item.setIcon(get_svg_icon("check", color="#22c55e", size=16))
            self.rec_list.addItem(item)

        # Key insights
        self.insights.clear()
        check_icon = get_svg_icon("check", color="#60a5fa", size=16)
        for ins in result.key_insights:
            item = QListWidgetItem("  " + ins.replace("**", ""))
            item.setIcon(check_icon)
            self.insights.addItem(item)

        # Tree & warnings
        self.tree_view.setText(result.tree_text or "—")
        self.warnings.setText(" ⚠️  " + " · ".join(result.warnings) if result.warnings else "")


# ---------------------------------------------------------------------------
# Export page
# ---------------------------------------------------------------------------

class ExportPage(QWidget):
    """Choose formats and export styled reports to disk with interactive confirmation."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.result: AnalysisResult | None = None
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)

        panel, layout = _panel("Export Analytics & Reports", icon_name="export")
        
        desc = QLabel(
            "Select which professional report formats to generate. Reports include self-contained "
            "glassmorphic dashboards, charts, storage health telemetry, and structured data."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #94a3b8; font-size: 12px; margin-bottom: 8px;")
        layout.addWidget(desc)

        self._checks: dict = {}
        formats = [
            ("html", "HTML Interactive Glass Dashboard (self-contained, offline SVG charts)"),
            ("md", "Markdown Executive Summary (formatted tables, health & insights)"),
            ("json", "JSON Structured Data (full telemetry, empty files & tree)"),
            ("csv", "CSV File-Type Breakdown (for Excel / PowerBI)"),
            ("txt", "Plain-Text Executive Summary"),
        ]
        for key, label in formats:
            cb = QCheckBox(label)
            cb.setChecked(True)
            self._checks[key] = cb
            layout.addWidget(cb)

        row = QHBoxLayout()
        row.setSpacing(10)
        self.dir_edit = QLineEdit()
        self.dir_edit.setPlaceholderText(
            "Output directory (defaults to 'folder_analysis' inside scanned folder)")
        browse = QPushButton("Browse…")
        browse.setObjectName("BrowseButton")
        browse.setIcon(get_svg_icon("folder", color="#cbd5e1", size=16))
        browse.clicked.connect(self._browse)
        row.addWidget(self.dir_edit, 1)
        row.addWidget(browse)
        layout.addLayout(row)

        self.export_btn = QPushButton(" Generate & Export Reports")
        self.export_btn.setObjectName("RunButton")
        self.export_btn.setIcon(get_svg_icon("export", color="#ffffff", size=18))
        self.export_btn.clicked.connect(self._export)
        layout.addWidget(self.export_btn)
        root.addWidget(panel)

        # Status panel
        status_panel, stat_lay = _panel("Export Status & Output Files", icon_name="check")
        self.status = QLabel("Ready — run a scan and select formats to export.")
        self.status.setWordWrap(True)
        self.status.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.status.setStyleSheet("color: #cbd5e1; font-size: 12px; line-height: 1.4;")
        stat_lay.addWidget(self.status)

        self.open_dir_btn = QPushButton("Open Output Folder")
        self.open_dir_btn.setObjectName("SecondaryButton")
        self.open_dir_btn.setIcon(get_svg_icon("folder", color="#60a5fa", size=16))
        self.open_dir_btn.setVisible(False)
        self.open_dir_btn.clicked.connect(self._open_output_folder)
        stat_lay.addWidget(self.open_dir_btn)

        root.addWidget(status_panel)
        root.addStretch(1)

        self._last_exported_dir: str = ""

    def set_result(self, result: AnalysisResult) -> None:
        self.result = result
        self.status.setText(
            f"Ready to export — {result.total_files:,} files indexed ({result.total_storage_formatted})."
            if result.has_data else "Run a scan first.")

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
        mapping = {"html": (export_html, "DASHBOARD.html", True),
                   "md": (export_markdown, "REPORT.md", True),
                   "json": (export_json, "DATA.json", False),
                   "csv": (export_csv, "DATA.csv", False),
                   "txt": (export_txt, "SUMMARY.txt", False)}
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
            
            output_msg = f"Successfully exported {len(written)} report(s) to:\n{base}\n\n"
            for p in written:
                output_msg += f"  • {os.path.basename(p)} ({os.path.getsize(p):,} bytes)\n"
            self.status.setText(output_msg)
            self.open_dir_btn.setVisible(True)
        except Exception as exc:
            self.status.setText(f"Export failed: {exc}")
            self.open_dir_btn.setVisible(False)
