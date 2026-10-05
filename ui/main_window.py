"""
Main window: command bar, sidebar navigation, stacked pages with fade
transitions, toast notifications and keyboard shortcuts.

Flow:  choose a folder -> Analyze -> a background ScanWorker streams
progress -> pages are refreshed with animated transitions and counters.
"""

from __future__ import annotations

import os

from PySide6.QtCore import (
    QEasingCurve, QPoint, QPropertyAnimation, QSize, QThread, QTimer, Qt,
)
from PySide6.QtGui import QAction, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QFrame, QGraphicsOpacityEffect, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QPushButton,
    QProgressBar, QSizePolicy, QStackedWidget, QVBoxLayout, QWidget,
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
    """QStackedWidget that transitions between pages with a clean fade-in."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._fade_anim: QPropertyAnimation | None = None

    def setCurrentIndex(self, index: int) -> None:
        if self._fade_anim is not None:
            self._fade_anim.stop()
            self._fade_anim = None

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
        anim.setDuration(220)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)

        def _cleanup():
            target.setGraphicsEffect(None)
            self._fade_anim = None

        anim.finished.connect(_cleanup)
        self._fade_anim = anim
        anim.start()


class Toast(QLabel):
    """Small floating notification that auto-hides."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("Toast")
        self.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setVisible(False)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._hide_animated)
        self._anim: QPropertyAnimation | None = None

    def show_message(self, text: str, kind: str = "info", ms: int = 2600) -> None:
        self.setProperty("toastKind", kind)
        self.style().unpolish(self)
        self.style().polish(self)
        self.setText(f"  {text}")
        self.adjustSize()
        self.resize(self.width() + 16, self.height() + 8)
        self._reposition()
        self.setVisible(True)
        self.raise_()

        effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(200)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start()
        self._anim = anim

        self._timer.start(ms)

    def _reposition(self) -> None:
        parent = self.parentWidget()
        if not parent:
            return
        x = parent.width() - self.width() - 30
        y = parent.height() - self.height() - 60
        self.move(max(20, x), max(20, y))

    def _hide_animated(self) -> None:
        effect = self.graphicsEffect()
        if effect is None:
            self.setVisible(False)
            return
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(260)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.InCubic)
        anim.finished.connect(lambda: self.setVisible(False))
        anim.start()
        self._anim = anim


class MainWindow(QWidget):
    """Root application window with command bar + sidebar and animations."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"Folder Analysis Pro v{__version__}")
        self.setObjectName("RootContainer")
        self.resize(1340, 860)
        self.setMinimumSize(1100, 720)

        self._thread: QThread | None = None
        self._worker: ScanWorker | None = None
        self._result = None

        self._build_ui()
        self._install_shortcuts()

        self._toast = Toast(self)
        self._toast.setVisible(False)

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

        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(20, 20, 20, 20)
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
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(14)

        # Brand
        badge = QLabel("PRO")
        badge.setObjectName("AppLogoBadge")
        layout.addWidget(badge)

        title_box = QVBoxLayout()
        title_box.setSpacing(1)
        title = QLabel("Folder Storage Analytics")
        title.setObjectName("TopBarTitle")
        sub = QLabel("Glassmorphic Deep Engine & Storage Optimizer")
        sub.setObjectName("TopBarSubtitle")
        title_box.addWidget(title)
        title_box.addWidget(sub)
        layout.addLayout(title_box)

        # Separator
        sep1 = QFrame()
        sep1.setObjectName("TopBarSeparator")
        sep1.setFrameShape(QFrame.VLine)
        sep1.setFixedHeight(34)
        layout.addWidget(sep1)

        # Path input
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Select or drop a folder path to analyze…")
        self.path_edit.returnPressed.connect(self.start_scan)
        self.path_edit.setMinimumWidth(320)
        layout.addWidget(self.path_edit, 1)

        self.browse_btn = QPushButton("Browse")
        self.browse_btn.setObjectName("BrowseButton")
        self.browse_btn.setIcon(get_svg_icon("folder", color="#cbd5e1", size=16))
        self.browse_btn.clicked.connect(self._browse)
        self.browse_btn.setToolTip("Browse for a folder to analyze  (Ctrl+O)")
        layout.addWidget(self.browse_btn)

        self.analyze_btn = QPushButton("Analyze")
        self.analyze_btn.setObjectName("RunButton")
        self.analyze_btn.setIcon(get_svg_icon("zap", color="#ffffff", size=16))
        self.analyze_btn.clicked.connect(self.start_scan)
        self.analyze_btn.setToolTip("Start scanning  (F5)")
        layout.addWidget(self.analyze_btn)

        self.cancel_btn = QPushButton("Stop")
        self.cancel_btn.setObjectName("CancelButton")
        self.cancel_btn.setIcon(get_svg_icon("cancel", color="#ffffff", size=16))
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel_scan)
        self.cancel_btn.setToolTip("Cancel the running scan  (Esc)")
        layout.addWidget(self.cancel_btn)

        # Separator
        sep2 = QFrame()
        sep2.setObjectName("TopBarSeparator")
        sep2.setFrameShape(QFrame.VLine)
        sep2.setFixedHeight(34)
        layout.addWidget(sep2)

        # Quick icon buttons
        self.export_btn_top = self._icon_button("export", "#cbd5e1",
                                                "Jump to Export  (Ctrl+E)")
        self.export_btn_top.clicked.connect(lambda: self._goto_page("export"))
        layout.addWidget(self.export_btn_top)

        self.help_btn = self._icon_button("keyboard", "#cbd5e1",
                                          "Keyboard shortcuts  (?)")
        self.help_btn.clicked.connect(self._show_shortcuts)
        layout.addWidget(self.help_btn)

        return bar

    def _icon_button(self, icon_name: str, color: str, tooltip: str) -> QPushButton:
        btn = QPushButton()
        btn.setObjectName("IconButton")
        btn.setIcon(get_svg_icon(icon_name, color=color, active_color="#ffffff", size=16))
        btn.setIconSize(QSize(16, 16))
        btn.setToolTip(tooltip)
        btn.setCursor(Qt.PointingHandCursor)
        return btn

    def _build_nav(self) -> QWidget:
        container = QWidget()
        container.setObjectName("NavContainer")
        container.setFixedWidth(232)
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 10, 0, 10)
        lay.setSpacing(4)

        section = QLabel("WORKSPACE")
        section.setObjectName("NavSectionLabel")
        lay.addWidget(section)

        self.nav = QListWidget()
        self.nav.setObjectName("NavList")
        self.nav.setIconSize(QSize(20, 20))
        for title, icon_name, _cls in PAGE_DEFS:
            item = QListWidgetItem("  " + title)
            item.setIcon(get_svg_icon(icon_name, color="#94a3b8",
                                      active_color="#ffffff", size=20))
            self.nav.addItem(item)
        lay.addWidget(self.nav)

        # Quick stats in sidebar
        lay.addStretch(1)
        stats = QFrame()
        stats.setObjectName("SidebarStat")
        sv = QVBoxLayout(stats)
        sv.setContentsMargins(12, 10, 12, 10)
        sv.setSpacing(2)

        l1 = QLabel("TOTAL INDEXED")
        l1.setObjectName("SidebarStatLabel")
        sv.addWidget(l1)

        self.sidebar_total = QLabel("—")
        self.sidebar_total.setObjectName("SidebarStatValue")
        sv.addWidget(self.sidebar_total)

        l2 = QLabel("DUPLICATE WASTE")
        l2.setObjectName("SidebarStatLabel")
        l2.setContentsMargins(0, 6, 0, 0)
        sv.addWidget(l2)

        self.sidebar_waste = QLabel("—")
        self.sidebar_waste.setObjectName("SidebarStatValue")
        sv.addWidget(self.sidebar_waste)

        lay.addWidget(stats)
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

        self.status_dot = QLabel("●")
        self.status_dot.setObjectName("StatusDot")
        self.status_dot.setProperty("state", "idle")
        layout.addWidget(self.status_dot)

        self.status_icon = QLabel()
        self.status_icon.setPixmap(get_svg_pixmap("sparkles", size=15, color="#60a5fa"))
        layout.addWidget(self.status_icon)

        self.status_label = QLabel("Ready — choose a folder and press Analyze.")
        self.status_label.setObjectName("StatusMessage")
        layout.addWidget(self.status_label, 1)

        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(6)
        self.progress.setFixedWidth(220)
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        self.status_meta = QLabel("")
        self.status_meta.setObjectName("StatusMeta")
        layout.addWidget(self.status_meta)

        return bar

    def _install_shortcuts(self) -> None:
        def sc(seq, handler):
            QShortcut(QKeySequence(seq), self, activated=handler)

        sc("Ctrl+O", self._browse)
        sc("F5", self.start_scan)
        sc("Ctrl+R", self.start_scan)
        sc("Esc", self.cancel_scan)
        sc("Ctrl+E", lambda: self._goto_page("export"))
        sc("Ctrl+1", lambda: self._set_nav(0))
        sc("Ctrl+2", lambda: self._set_nav(1))
        sc("Ctrl+3", lambda: self._set_nav(2))
        sc("Ctrl+4", lambda: self._set_nav(3))
        sc("Ctrl+5", lambda: self._set_nav(4))
        sc("Ctrl+6", lambda: self._set_nav(5))
        sc("?", self._show_shortcuts)

    # -- navigation helpers --------------------------------------------------

    def _on_nav_changed(self, index: int) -> None:
        if 0 <= index < self.stack.count():
            self.stack.setCurrentIndex(index)

    def _set_nav(self, index: int) -> None:
        if 0 <= index < self.nav.count():
            self.nav.setCurrentRow(index)

    def _goto_page(self, key: str) -> None:
        for i, (title, icon, _cls) in enumerate(PAGE_DEFS):
            if icon == key or title.lower().startswith(key):
                self._set_nav(i)
                return

    # -- actions -------------------------------------------------------------

    def _browse(self) -> None:
        start = self.path_edit.text().strip() or os.path.expanduser("~")
        chosen = QFileDialog.getExistingDirectory(self, "Choose folder to analyze", start)
        if chosen:
            self.path_edit.setText(chosen)
            self.start_scan()

    def start_scan(self) -> None:
        if self._thread is not None:
            return
        text = self.path_edit.text().strip()
        path = os.path.abspath(os.path.expanduser(text)) if text else ""
        if not path or not os.path.isdir(path):
            self._set_status("error", "warning", "Please select a valid directory first.")
            self._toast.show_message("Invalid or missing directory.", "error")
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
        self._set_status("running", "search", "Scanning…")
        self.progress.setRange(0, 0)

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
            self._set_status("warn", "warning", "Cancelling scan…")

    # -- worker signal handlers ---------------------------------------------

    def _on_progress(self, files: int, dirs: int) -> None:
        self.status_label.setText(
            f"Scanning — {files:,} files · {dirs:,} folders discovered")
        self.status_meta.setText("live")

    def _on_finished(self, result) -> None:
        self._result = result
        for page in self.pages:
            page.set_result(result)

        summary = (
            f"{result.root_name}: {result.total_files:,} files · "
            f"{result.total_storage_formatted} · "
            f"Health: {result.storage_efficiency_score}/100 "
            f"({result.storage_health_label}) · "
            f"{result.scan_duration_seconds}s"
        )
        if result.duplicate_groups:
            summary += f" · Wasted: {result.duplicate_wasted_formatted}"

        self._set_status("ok", "check", summary)
        self.status_meta.setText(f"{len(result.duplicate_groups)} dup. groups")

        # Sidebar quick stats
        self.sidebar_total.setText(
            f"{result.total_files:,} / {result.total_storage_formatted}")
        self.sidebar_waste.setText(
            result.duplicate_wasted_formatted if result.duplicate_groups else "None")

        # Toast
        if result.duplicate_groups and result.actionable_savings_bytes > 0:
            self._toast.show_message(
                f"Scan complete · {result.actionable_savings_formatted} recoverable",
                "warning")
        else:
            self._toast.show_message("Scan complete — storage looks healthy.", "success")

        self._teardown_worker()
        self._set_busy(False)

    def _on_failed(self, message: str) -> None:
        self._set_status("error", "cancel", f"Scan failed: {message}")
        self.status_meta.setText("")
        self._toast.show_message(f"Scan failed: {message}", "error")
        self._teardown_worker()
        self._set_busy(False)

    def _on_cancelled(self) -> None:
        self._set_status("warn", "warning", "Scan cancelled by user.")
        self.status_meta.setText("")
        self._toast.show_message("Scan cancelled.", "warning")
        self._teardown_worker()
        self._set_busy(False)

    # -- helpers -------------------------------------------------------------

    def _set_status(self, state: str, icon_name: str, text: str) -> None:
        self.status_dot.setProperty("state", state)
        self.status_dot.style().unpolish(self.status_dot)
        self.status_dot.style().polish(self.status_dot)
        colors = {
            "idle": "#64748b", "running": "#00d2ff",
            "ok": "#22c55e", "warn": "#f59e0b", "error": "#ef4444",
        }
        self.status_icon.setPixmap(
            get_svg_pixmap(icon_name, size=15, color=colors.get(state, "#60a5fa")))
        self.status_label.setText(text)

    def _show_shortcuts(self) -> None:
        self._toast.show_message(
            "Ctrl+O browse · F5 scan · Esc stop · Ctrl+E export · Ctrl+1-6 pages",
            "info", ms=4200)

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
        self.browse_btn.setEnabled(not busy)
        if message is not None:
            self.status_label.setText(message)

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        if getattr(self, "_toast", None) is not None and self._toast.isVisible():
            self._toast._reposition()

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._worker is not None:
            self._worker.cancel()
        self._teardown_worker()
        super().closeEvent(event)