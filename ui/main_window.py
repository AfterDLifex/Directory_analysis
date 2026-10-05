"""
Main window: top bar, sidebar navigation and stacked pages with glassmorphic visuals and smooth animations.

Flow:  choose a folder -> Analyze -> a background ScanWorker streams
progress -> pages are refreshed with animated transitions and counters.
"""

from __future__ import annotations

import os

from PySide6.QtCore import (
    QEasingCurve, QPropertyAnimation, QSize, QThread, Qt,
)
from PySide6.QtWidgets import (
    QFileDialog, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QPushButton, QProgressBar, QStackedWidget,
    QVBoxLayout, QWidget,
)

from folder_analyzer import __version__
from folder_analyzer.models import AnalysisConfig

from .icons import get_svg_icon, get_svg_pixmap
from .pages import (
    ChartsPage, DuplicatesPage, ExportPage, FilesPage, InsightsPage,
    OverviewPage,
)
from .scan_worker import ScanWorker

PAGE_DEFS = [
    ("Overview", "overview", OverviewPage),
    ("Visual Charts", "charts", ChartsPage),
    ("File Explorer", "files", FilesPage),
    ("Duplicates", "duplicates", DuplicatesPage),
    ("Deep Insights", "insights", InsightsPage),
    ("Export Data", "export", ExportPage),
]


class AnimatedStackedWidget(QStackedWidget):
    """QStackedWidget that transitions between pages with a clean fade-in animation and no overlapping."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._fade_anim: QPropertyAnimation | None = None

    def setCurrentIndex(self, index: int) -> None:
        # Stop any in-flight animation before switching
        if self._fade_anim is not None:
            self._fade_anim.stop()
            self._fade_anim = None

        # Clean graphics effect from the current widget so it doesn't linger
        curr = self.currentWidget()
        if curr is not None:
            curr.setGraphicsEffect(None)

        super().setCurrentIndex(index)
        target = self.widget(index)
        if not target:
            return

        effect = QGraphicsOpacityEffect(target)
        target.setGraphicsEffect(effect)

        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(200)
        anim.setStartValue(0.15)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)

        def _cleanup():
            target.setGraphicsEffect(None)
            self._fade_anim = None

        anim.finished.connect(_cleanup)
        self._fade_anim = anim
        anim.start()


class MainWindow(QWidget):
    """Root application window with glassmorphism aesthetics and animated transitions."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"Folder Analysis Pro v{__version__}")
        self.setObjectName("RootContainer")
        self.resize(1220, 800)
        self.setMinimumSize(1000, 680)
        self._thread: QThread | None = None
        self._worker: ScanWorker | None = None
        self._result = None
        self._build_ui()

    # -- UI construction -----------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_top_bar())

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self._build_nav())
        
        # Main content area with padding
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(18, 18, 18, 18)
        content_layout.setSpacing(0)
        content_layout.addWidget(self._build_pages())

        body.addWidget(content_container, 1)
        root.addLayout(body, 1)
        root.addWidget(self._build_status_bar())

        self.nav.currentRowChanged.connect(self._on_nav_changed)
        self.nav.setCurrentRow(0)

    def _build_top_bar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("TopBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 14, 20, 14)
        layout.setSpacing(12)

        # Brand badge & title
        badge = QLabel("PRO")
        badge.setObjectName("AppLogoBadge")
        layout.addWidget(badge)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title = QLabel("Folder Storage Analytics")
        title.setObjectName("TopBarTitle")
        sub = QLabel("Glassmorphic Deep Engine & Storage Optimizer")
        sub.setObjectName("TopBarSubtitle")
        title_box.addWidget(title)
        title_box.addWidget(sub)
        layout.addLayout(title_box)

        layout.addSpacing(16)

        # Folder search bar
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Select or enter folder path to analyze…")
        self.path_edit.returnPressed.connect(self.start_scan)
        layout.addWidget(self.path_edit, 1)

        browse = QPushButton("Browse…")
        browse.setObjectName("BrowseButton")
        browse.setIcon(get_svg_icon("folder", color="#cbd5e1", size=16))
        browse.clicked.connect(self._browse)
        layout.addWidget(browse)

        self.analyze_btn = QPushButton(" Analyze")
        self.analyze_btn.setObjectName("RunButton")
        self.analyze_btn.setIcon(get_svg_icon("zap", color="#ffffff", size=16))
        self.analyze_btn.clicked.connect(self.start_scan)
        layout.addWidget(self.analyze_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("CancelButton")
        self.cancel_btn.setIcon(get_svg_icon("cancel", color="#ffffff", size=16))
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel_scan)
        layout.addWidget(self.cancel_btn)
        return bar

    def _build_nav(self) -> QWidget:
        container = QWidget()
        container.setObjectName("NavContainer")
        container.setFixedWidth(220)
        lay = QVBoxLayout(container)
        lay.setContentsMargins(8, 14, 8, 14)
        lay.setSpacing(6)

        self.nav = QListWidget()
        self.nav.setObjectName("NavList")
        self.nav.setIconSize(QSize(20, 20))
        for title, icon_name, _cls in PAGE_DEFS:
            item = QListWidgetItem("  " + title)
            item.setIcon(get_svg_icon(icon_name, color="#94a3b8", active_color="#ffffff", size=20))
            self.nav.addItem(item)
        lay.addWidget(self.nav)
        return container

    def _build_pages(self) -> QStackedWidget:
        self.stack = AnimatedStackedWidget()
        self.pages = []
        for _title, _icon, cls in PAGE_DEFS:
            page = cls()
            self.pages.append(page)
            self.stack.addWidget(page)
        return self.stack

    def _build_status_bar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("StatusBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 8, 20, 8)
        layout.setSpacing(14)

        self.status_icon = QLabel()
        self.status_icon.setPixmap(get_svg_pixmap("sparkles", size=16, color="#60a5fa"))
        layout.addWidget(self.status_icon)

        self.status_label = QLabel("Ready — choose a folder and press Analyze.")
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(6)
        self.progress.setRange(0, 1)
        self.progress.setValue(0)

        layout.addWidget(self.status_label, 1)
        layout.addWidget(self.progress, 1)
        return bar

    def _on_nav_changed(self, index: int) -> None:
        if 0 <= index < self.stack.count():
            self.stack.setCurrentIndex(index)

    # -- actions -------------------------------------------------------------

    def _browse(self) -> None:
        start = self.path_edit.text().strip() or os.path.expanduser("~")
        chosen = QFileDialog.getExistingDirectory(self, "Choose folder to analyze", start)
        if chosen:
            self.path_edit.setText(chosen)
            self.start_scan()

    def start_scan(self) -> None:
        if self._thread is not None:
            return  # a scan is already running
        text = self.path_edit.text().strip()
        path = os.path.abspath(os.path.expanduser(text)) if text else ""
        if not path or not os.path.isdir(path):
            self.status_icon.setPixmap(get_svg_pixmap("warning", size=16, color="#f87171"))
            self.status_label.setText("Please select a valid directory first.")
            return
        cfg = AnalysisConfig(
            folder_path=path,
            top_n=30,
            include_hidden=False,
            detect_duplicates=True,
            tree_max_depth=3,
            largest_n=50,
            oldest_n=50,
        )
        self._set_busy(True, f"Indexing and analyzing {path} …")
        self.status_icon.setPixmap(get_svg_pixmap("search", size=16, color="#38bdf8"))
        self.progress.setRange(0, 0)  # indeterminate animated pulse

        self._thread = QThread(self)
        self._worker = ScanWorker(cfg)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progressChanged.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.cancelled.connect(self._on_cancelled)
        self._thread.start()

    def cancel_scan(self) -> None:
        if self._worker is not None:
            self._worker.cancel()
            self.status_label.setText("Cancelling scan…")

    # -- worker signal handlers ------------------------------------------------

    def _on_progress(self, files: int, dirs: int) -> None:
        self.status_label.setText(f"Scanning: {files:,} files discovered across {dirs:,} folders…")

    def _on_finished(self, result) -> None:
        self._result = result
        for page in self.pages:
            page.set_result(result)
        summary = (
            f"{result.root_name}: {result.total_files:,} files · "
            f"{result.total_storage_formatted} · "
            f"Health: {result.storage_efficiency_score}/100 ({result.storage_health_label}) · "
            f"{result.scan_duration_seconds}s"
        )
        if result.duplicate_groups:
            summary += f" · Wasted: {result.duplicate_wasted_formatted}"
        self.status_icon.setPixmap(get_svg_pixmap("check", size=16, color="#22c55e"))
        self.status_label.setText(summary)
        self._teardown_worker()
        self._set_busy(False)

    def _on_failed(self, message: str) -> None:
        self.status_icon.setPixmap(get_svg_pixmap("cancel", size=16, color="#ef4444"))
        self.status_label.setText(f"Scan failed: {message}")
        self._teardown_worker()
        self._set_busy(False)

    def _on_cancelled(self) -> None:
        self.status_icon.setPixmap(get_svg_pixmap("warning", size=16, color="#f59e0b"))
        self.status_label.setText("Scan cancelled by user.")
        self._teardown_worker()
        self._set_busy(False)

    # -- helpers -------------------------------------------------------------

    def _teardown_worker(self) -> None:
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait(3000)
        if self._worker is not None:
            self._worker.deleteLater()
        if self._thread is not None:
            self._thread.deleteLater()
        self._thread = None
        self._worker = None
        self.progress.setRange(0, 1)
        self.progress.setValue(0)

    def _set_busy(self, busy: bool, message=None) -> None:
        self.analyze_btn.setEnabled(not busy)
        self.cancel_btn.setEnabled(busy)
        self.path_edit.setEnabled(not busy)
        if message is not None:
            self.status_label.setText(message)

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        if self._worker is not None:
            self._worker.cancel()
        self._teardown_worker()
        super().closeEvent(event)