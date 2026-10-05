"""
Main window: top bar, sidebar navigation and stacked pages with glassmorphic visuals and smooth animations.

Flow:  choose a folder -> Analyze -> a background ScanWorker streams
progress -> pages are refreshed with animated transitions and counters.
"""

from __future__ import annotations

import os

from PySide6.QtCore import (
    QEasingCurve, QParallelAnimationGroup, QPropertyAnimation, QThread, Qt,
)
from PySide6.QtWidgets import (
    QFileDialog, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QPushButton, QProgressBar, QStackedWidget, QVBoxLayout,
    QWidget,
)

from folder_analyzer import __version__
from folder_analyzer.models import AnalysisConfig

from .pages import (
    ChartsPage, DuplicatesPage, ExportPage, FilesPage, InsightsPage,
    OverviewPage,
)
from .scan_worker import ScanWorker

PAGES = [
    ("📊 Overview", OverviewPage),
    ("📈 Visual Charts", ChartsPage),
    ("📁 File Explorer", FilesPage),
    ("⚠️ Duplicates", DuplicatesPage),
    ("💡 Deep Insights", InsightsPage),
    ("🚀 Export Data", ExportPage),
]


class AnimatedStackedWidget(QStackedWidget):
    """QStackedWidget that transitions between pages with a smooth fade animation."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._fade_anim = None

    def setCurrentIndex(self, index: int) -> None:
        widget = self.widget(index)
        if not widget:
            super().setCurrentIndex(index)
            return

        super().setCurrentIndex(index)
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)

        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(240)
        anim.setStartValue(0.2)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        self._fade_anim = anim
        anim.start()


class MainWindow(QWidget):
    """Root application window with glassmorphism aesthetics and animated transitions."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"Folder Analysis Pro v{__version__}")
        self.setObjectName("RootContainer")
        self.resize(1200, 780)
        self.setMinimumSize(980, 660)
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
        title_box.setSpacing(1)
        title = QLabel("Folder Storage Analytics")
        title.setObjectName("TopBarTitle")
        sub = QLabel("Glassmorphic Deep Engine")
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
        browse.clicked.connect(self._browse)
        layout.addWidget(browse)

        self.analyze_btn = QPushButton("⚡ Analyze")
        self.analyze_btn.setObjectName("RunButton")
        self.analyze_btn.clicked.connect(self.start_scan)
        layout.addWidget(self.analyze_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("CancelButton")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel_scan)
        layout.addWidget(self.cancel_btn)
        return bar

    def _build_nav(self) -> QWidget:
        container = QWidget()
        container.setObjectName("NavContainer")
        container.setFixedWidth(210)
        lay = QVBoxLayout(container)
        lay.setContentsMargins(6, 12, 6, 12)
        lay.setSpacing(4)

        self.nav = QListWidget()
        self.nav.setObjectName("NavList")
        for name, _cls in PAGES:
            self.nav.addItem(name)
        lay.addWidget(self.nav)
        return container

    def _build_pages(self) -> QStackedWidget:
        self.stack = AnimatedStackedWidget()
        self.pages = []
        for _name, cls in PAGES:
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

        self.status_label = QLabel("✨ Ready — choose a folder and press Analyze.")
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(6)
        self.progress.setRange(0, 1)
        self.progress.setValue(0)

        layout.addWidget(self.status_label, 1)
        layout.addWidget(self.progress, 1)
        return bar

    def _on_nav_changed(self, index: int) -> None:
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
            self.status_label.setText("⚠️ Please select a valid directory first.")
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
        self._set_busy(True, f"🔍 Indexing and analyzing {path} …")
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
            f"✨ {result.root_name}: {result.total_files:,} files · "
            f"{result.total_storage_formatted} · "
            f"{result.scan_duration_seconds}s scan"
        )
        if result.duplicate_groups:
            summary += f" · ⚠️ {result.duplicate_wasted_formatted} duplicate waste"
        self.status_label.setText(summary)
        self._teardown_worker()
        self._set_busy(False)

    def _on_failed(self, message: str) -> None:
        self.status_label.setText(f"❌ Scan failed: {message}")
        self._teardown_worker()
        self._set_busy(False)

    def _on_cancelled(self) -> None:
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