"""
Main window: sidebar navigation, stacked pages, scan orchestration, toasts.

Layout
------
* top bar   - branding, folder picker, scan controls, quick actions
* sidebar   - sectioned navigation + live aggregate stats
* content   - animated stacked pages (see :mod:`ui.pages`)
* statusbar - scan state, progress and metadata

The export flow runs on a worker thread (:mod:`ui.export_worker`) and is
visualised by a non-blocking :class:`~ui.modals.ExportOverlay`, so the
window - including the sidebar - stays interactive while reports are written.
The overlay's success state offers an explicit **Back to Analysis** action.
"""

from __future__ import annotations

import os
from typing import Callable, Dict, List, Optional

from PySide6.QtCore import QSize, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QProgressBar, QPushButton, QVBoxLayout, QWidget,
)

from folder_analyzer import __version__
from folder_analyzer.models import AnalysisResult

from .animations import AnimatedStackedWidget, stagger_in
from .export_worker import ExportWorker, plan
from .icons import get_svg_icon, get_svg_pixmap
from .modals import (
    ConfirmOverlay, ExportOverlay, ShortcutsOverlay, ThemeOverlay, open_path,
)
from .pages import (
    AdvancedPage, ChartsPage, DuplicatesPage, FilesPage, FileViewerPage,
    InsightsPage, OverviewPage, ReportsPage, SettingsPage, TimelinePage,
)
from .scan_worker import ScanWorker
from .settings_store import active_config, config_for_scan
from .theme import ACCENTS, THEMES, ThemeManager, ThemeTokens
from .toast import ToastHost
from .widgets import tool_button

#: (section, page key, nav label, icon name, page class).
#: The order here defines sidebar order and the Ctrl+N shortcuts.
PAGE_DEFS: List[tuple] = [
    ("Analysis", "overview", "Overview", "overview", OverviewPage),
    ("Analysis", "charts", "Visual Charts", "charts", ChartsPage),
    ("Analysis", "timeline", "Timeline", "clock", TimelinePage),
    ("Analysis", "explorer", "File Explorer", "files", FilesPage),
    ("Analysis", "viewer", "File Viewer", "search", FileViewerPage),
    ("Diagnostics", "duplicates", "Duplicates", "duplicates", DuplicatesPage),
    ("Diagnostics", "advanced", "Advanced", "sliders", AdvancedPage),
    ("Diagnostics", "insights", "Deep Insights", "insights", InsightsPage),
    ("System", "reports", "Reports & Export", "export", ReportsPage),
    ("System", "settings", "Settings", "settings", SettingsPage),
]

#: Flat page-key list in navigation order (shortcuts use PAGE_KEYS[:9]).
PAGE_KEYS: List[str] = [d[1] for d in PAGE_DEFS]

#: Section label per page key, used by the sidebar headers.
PAGE_SECTION: Dict[str, str] = {d[1]: d[0] for d in PAGE_DEFS}


class MainWindow(QWidget):
    """Application shell: navigation, scanning, exports and overlays."""

    #: Emitted whenever the active page changes (page key, not index).
    pageChanged = Signal(str)

    def __init__(self, theme: Optional[str] = None) -> None:
        super().__init__()
        self.setWindowTitle(f"Folder Analysis Pro v{__version__}")
        self.setObjectName("RootContainer")
        self.resize(1400, 900)
        self.setMinimumSize(1120, 720)

        self._thread: Optional[QThread] = None
        self._worker: Optional[ScanWorker] = None
        self._result: Optional[AnalysisResult] = None

        self._export_thread: Optional[QThread] = None
        self._export_worker: Optional[ExportWorker] = None
        self._export_formats: List[str] = []
        self._export_dir = ""
        self._export_failed = 0
        self._last_export_dir = ""

        self._pages: Dict[str, object] = {}
        self._nav: Optional[QListWidget] = None
        self._row_for_key: Dict[str, int] = {}
        self._key_for_row: Dict[int, str] = {}

        self.manager: Optional[ThemeManager] = None

        self._build_ui()
        self.manager = ThemeManager.instance()
        self._wire_overlays()
        self._wire_viewer_callbacks()
        self._install_shortcuts()
        if theme:
            self.manager.set_theme(theme)

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_top_bar())

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self._build_nav())

        content = QWidget()
        content_lay = QVBoxLayout(content)
        content_lay.setContentsMargins(22, 20, 22, 20)
        content_lay.setSpacing(0)
        content_lay.addWidget(self._build_pages())
        body.addWidget(content, 1)
        root.addLayout(body, 1)
        root.addWidget(self._build_status_bar())

        self._toasts = ToastHost(self)
        self._goto("overview")

    def _build_pages(self) -> AnimatedStackedWidget:
        self.stack = AnimatedStackedWidget()
        for _section, key, _label, _icon, cls in PAGE_DEFS:
            page = cls()
            self._pages[key] = page
            self.stack.addWidget(page)
        return self.stack

    def _separator(self) -> QFrame:
        sep = QFrame()
        sep.setObjectName("TopBarSeparator")
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFixedHeight(32)
        return sep

    # ------------------------------------------------------------------
    # Top bar
    # ------------------------------------------------------------------

    def _build_top_bar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("TopBar")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(20, 11, 20, 11)
        lay.setSpacing(12)

        badge = QLabel("PRO")
        badge.setObjectName("AppLogoBadge")
        lay.addWidget(badge)

        titles = QVBoxLayout()
        titles.setSpacing(1)
        title = QLabel("Folder Storage Analytics")
        title.setObjectName("TopBarTitle")
        sub = QLabel("Deep engine · storage optimizer")
        sub.setObjectName("TopBarSubtitle")
        titles.addWidget(title)
        titles.addWidget(sub)
        lay.addLayout(titles)

        lay.addWidget(self._separator())

        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText(
            "Select or drop a folder path to analyze…")
        self.path_edit.setClearButtonEnabled(True)
        self.path_edit.returnPressed.connect(self.start_scan)
        self.path_edit.setMinimumWidth(280)
        lay.addWidget(self.path_edit, 1)

        browse = QPushButton("Browse")
        browse.setObjectName("GhostButton")
        browse.setIcon(get_svg_icon("folder", color="#cbd5e1", size=16))
        browse.clicked.connect(self._browse)
        browse.setToolTip("Browse for a folder to analyze  (Ctrl+O)")
        self.browse_btn = browse
        lay.addWidget(browse)

        analyze = QPushButton("Analyze")
        analyze.setObjectName("RunButton")
        analyze.setIcon(get_svg_icon("zap", color="#ffffff", size=16))
        analyze.clicked.connect(self.start_scan)
        analyze.setToolTip("Start scanning  (F5)")
        self.analyze_btn = analyze
        lay.addWidget(analyze)

        cancel = QPushButton("Stop")
        cancel.setObjectName("DangerButton")
        cancel.setIcon(get_svg_icon("cancel", color="#ffffff", size=16))
        cancel.setEnabled(False)
        cancel.clicked.connect(self.cancel_scan)
        cancel.setToolTip("Cancel the running scan  (Esc)")
        self.cancel_btn = cancel
        lay.addWidget(cancel)

        lay.addWidget(self._separator())

        self.export_btn_top = tool_button(
            "download", "Reports & Export  (Ctrl+E)",
            lambda: self._goto("reports"), role="text_dim")
        lay.addWidget(self.export_btn_top)

        self.theme_btn = tool_button(
            "sparkles", "Appearance  (Ctrl+T)", self._open_theme_picker,
            role="text_dim")
        lay.addWidget(self.theme_btn)

        self.settings_btn = tool_button(
            "settings", "Settings  (Ctrl+,)", lambda: self._goto("settings"),
            role="text_dim")
        lay.addWidget(self.settings_btn)

        help_btn = tool_button(
            "keyboard", "Keyboard shortcuts  (?)", self._show_shortcuts,
            role="text_dim")
        self.help_btn = help_btn
        lay.addWidget(help_btn)
        return bar


# ----------------------------------------------------------------------
    # Sidebar with section headers
    # ----------------------------------------------------------------------

    def _build_nav(self) -> QWidget:
        container = QWidget()
        container.setObjectName("NavContainer")
        container.setFixedWidth(236)
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 8, 0, 8)
        lay.setSpacing(2)

        brand = QLabel("WORKSPACE")
        brand.setObjectName("NavSectionLabel")
        lay.addWidget(brand)

        # Grouped nav: a non-selectable header row per section, then pages.
        self.nav = QListWidget()
        self.nav.setObjectName("NavList")
        self.nav.setIconSize(self.nav.iconSize())

        row = 0
        current_section = None
        for section, key, label, icon, _cls in PAGE_DEFS:
            if section != current_section:
                header = QListWidgetItem(section.upper())
                header.setFlags(Qt.ItemFlag.NoItemFlags)
                size = header.sizeHint()
                header.setSizeHint(size + QSize(0, 22))
                self.nav.addItem(header)
                current_section = section
                row += 1
            item = QListWidgetItem("  " + label)
            item.setData(Qt.ItemDataRole.UserRole, key)
            item.setIcon(get_svg_icon(icon, color="#94a3b8",
                                      active_color="#ffffff", size=20))
            self.nav.addItem(item)
            self._row_for_key[key] = row
            self._key_for_row[row] = key
            row += 1
        lay.addWidget(self.nav, 1)

        hint = QLabel("Ctrl+1…9 jump · F5 rescan · ? help")
        hint.setObjectName("NavHint")
        lay.addWidget(hint)

        stats = QFrame()
        stats.setObjectName("SidebarStat")
        stat_lay = QVBoxLayout(stats)
        stat_lay.setContentsMargins(12, 10, 12, 10)
        stat_lay.setSpacing(2)

        indexed = QLabel("TOTAL INDEXED")
        indexed.setObjectName("SidebarStatLabel")
        stat_lay.addWidget(indexed)
        self.sidebar_total = QLabel("—")
        self.sidebar_total.setObjectName("SidebarStatValue")
        stat_lay.addWidget(self.sidebar_total)

        waste = QLabel("DUPLICATE WASTE")
        waste.setObjectName("SidebarStatLabel")
        waste.setContentsMargins(0, 8, 0, 0)
        stat_lay.addWidget(waste)
        self.sidebar_waste = QLabel("—")
        self.sidebar_waste.setObjectName("SidebarStatValue")
        stat_lay.addWidget(self.sidebar_waste)
        lay.addWidget(stats)

        self.nav.currentRowChanged.connect(self._on_nav_row)
        return container

    # ------------------------------------------------------------------
    # Status bar
    # ------------------------------------------------------------------

    def _build_status_bar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("StatusBar")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(20, 7, 20, 7)
        lay.setSpacing(12)

        self.status_dot = QLabel("●")
        self.status_dot.setObjectName("StatusDot")
        self.status_dot.setProperty("state", "idle")
        lay.addWidget(self.status_dot)

        self.status_icon = QLabel()
        self.status_icon.setPixmap(get_svg_pixmap(
            "sparkles", size=15, color="#60a5fa"))
        lay.addWidget(self.status_icon)

        self.status_label = QLabel("Ready — choose a folder and press Analyze.")
        self.status_label.setObjectName("StatusMessage")
        lay.addWidget(self.status_label, 1)

        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(6)
        self.progress.setFixedWidth(220)
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress.setVisible(False)
        lay.addWidget(self.progress)

        self.status_meta = QLabel("")
        self.status_meta.setObjectName("StatusMeta")
        lay.addWidget(self.status_meta)
        return bar

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _on_nav_row(self, row: int) -> None:
        key = self._key_for_row.get(row)
        if key is not None:
            self.stack.setCurrentIndex(PAGE_KEYS.index(key))

    def _goto(self, key: str) -> None:
        """Select the sidebar row for ``key`` (no-op when unknown)."""
        row = self._row_for_key.get(key)
        if row is None:
            return
        if self.nav.currentRow() != row:
            self.nav.setCurrentRow(row)
        else:
            self.stack.setCurrentIndex(PAGE_KEYS.index(key))
        self.pageChanged.emit(key)

    def _goto_page_index(self, index: int) -> None:
        if 0 <= index < len(PAGE_KEYS):
            self._goto(PAGE_KEYS[index])


# ----------------------------------------------------------------------
    # Scanning
    # ----------------------------------------------------------------------

    def _browse(self) -> None:
        start = self.path_edit.text().strip() or os.path.expanduser("~")
        chosen = QFileDialog.getExistingDirectory(
            self, "Choose folder to analyze", start)
        if chosen:
            self.path_edit.setText(chosen)
            self.start_scan()

    def start_scan(self) -> None:
        """Validate the path and kick off a background scan."""
        if self._thread is not None:
            self._toasts.show("A scan is already running.", "warning")
            return
        text = self.path_edit.text().strip()
        path = os.path.abspath(os.path.expanduser(text)) if text else ""
        if not path or not os.path.isdir(path):
            self._set_status("error", "warning",
                             "Please select a valid directory first.")
            self._toasts.show("Invalid or missing directory.", "error")
            return

        config = config_for_scan(path)
        self._set_busy(True)
        self._set_status("running", "search", f"Indexing {path} …")
        self.progress.setRange(0, 0)
        self.progress.setVisible(True)

        self._thread = QThread(self)
        self._worker = ScanWorker(config)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progressChanged.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.cancelled.connect(self._on_cancelled)
        self._thread.start()

    def cancel_scan(self) -> None:
        """Ask the running scan to stop as soon as possible."""
        if self._worker is None:
            return
        self._worker.cancel()
        self._set_status("warn", "warning", "Cancelling scan…")

    def _on_progress(self, files: int, dirs: int) -> None:
        self.status_label.setText(
            f"Scanning — {files:,} files · {dirs:,} folders discovered")
        self.status_meta.setText("live")

    def _on_finished(self, result: AnalysisResult) -> None:
        self._result = result
        for page in self._pages.values():
            page.set_result(result)

        summary = (
            f"{result.root_name}: {result.total_files:,} files · "
            f"{result.total_storage_formatted} · "
            f"Health {result.storage_efficiency_score}/100 "
            f"({result.storage_health_label}) · "
            f"{result.scan_duration_seconds}s")
        if result.duplicate_groups:
            summary += f" · Wasted {result.duplicate_wasted_formatted}"

        self._set_status("ok", "check", summary)
        self.status_meta.setText(f"{len(result.duplicate_groups)} dup. groups")
        self.sidebar_total.setText(
            f"{result.total_files:,} / {result.total_storage_formatted}")
        self.sidebar_waste.setText(
            result.duplicate_wasted_formatted if result.duplicate_groups
            else "None")

        if result.actionable_savings_bytes > 0:
            self._toasts.show(
                f"Scan complete · {result.actionable_savings_formatted} "
                f"recoverable", "warning")
        else:
            self._toasts.show("Scan complete — storage looks healthy.",
                              "success")

        self._teardown_worker()
        self._set_busy(False)
        self.progress.setVisible(False)

    def _on_failed(self, message: str) -> None:
        self._set_status("error", "cancel", f"Scan failed: {message}")
        self.status_meta.setText("")
        self._toasts.show(f"Scan failed: {message}", "error")
        self._teardown_worker()
        self._set_busy(False)
        self.progress.setVisible(False)

    def _on_cancelled(self) -> None:
        self._set_status("warn", "warning", "Scan cancelled by user.")
        self.status_meta.setText("")
        self._toasts.show("Scan cancelled.", "warning")
        self._teardown_worker()
        self._set_busy(False)
        self.progress.setVisible(False)

    def _teardown_worker(self) -> None:
        """Stop and release the scan thread, tolerating a slow shutdown."""
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

    def _set_busy(self, busy: bool) -> None:
        self.analyze_btn.setEnabled(not busy)
        self.cancel_btn.setEnabled(busy)
        self.path_edit.setEnabled(not busy)
        self.browse_btn.setEnabled(not busy)

    def _set_status(self, state: str, icon_name: str, text: str) -> None:
        """Update the coloured dot, icon and message in the status bar."""
        self.status_dot.setProperty("state", state)
        self.status_dot.style().unpolish(self.status_dot)
        self.status_dot.style().polish(self.status_dot)
        colors = {"idle": "#64748b", "running": "#00d2ff", "ok": "#22c55e",
                  "warn": "#f59e0b", "error": "#ef4444"}
        self.status_icon.setPixmap(get_svg_pixmap(
            icon_name, size=15, color=colors.get(state, "#60a5fa")))
        self.status_label.setText(text)


# ----------------------------------------------------------------------
    # Export (non-blocking: worker thread + live overlay)
    # ----------------------------------------------------------------------

    def start_export(self, output_dir: str, formats: List[str]) -> None:
        """Start an export on a worker thread and show the progress overlay.

        The overlay is a child widget rather than a modal dialog, so the whole
        window - including the sidebar - stays interactive while the reports
        are written. That is the fix for the "cannot get back to the analyser
        after downloading/exporting" problem.
        """
        if self._result is None or not self._result.has_data:
            self._toasts.show("Run a scan first to enable exports.", "warning")
            self._goto("reports")
            return
        if not formats:
            self._toasts.show("Pick at least one report format.", "warning")
            return
        if self._export_thread is not None:
            self._toasts.show("An export is already running.", "warning")
            return

        self._export_dir = output_dir
        self._export_formats = list(formats)
        self._export_failed = 0

        self.export_overlay.begin("Exporting reports",
                                  plan(self._export_formats))
        self._goto("reports")
        self._set_export_busy(True)

        self._export_thread = QThread(self)
        self._export_worker = ExportWorker(
            self._result, self._export_formats, output_dir)
        self._export_worker.moveToThread(self._export_thread)
        self._export_thread.started.connect(self._export_worker.run)
        self._export_worker.stageStarted.connect(
            self.export_overlay.start_stage)
        self._export_worker.stageFinished.connect(
            self.export_overlay.finish_stage)
        self._export_worker.stageFailed.connect(self._on_export_stage_failed)
        self._export_worker.completed.connect(self._on_export_done)
        self._export_worker.failed.connect(self._on_export_failed)
        self._export_thread.start()

    def _on_export_stage_failed(self, index: int, detail: str) -> None:
        """A single format failed; the remaining ones still run."""
        self._export_failed += 1
        self.export_overlay.fail_stage(index, detail)

    def _on_export_done(self, written: List[str], output_dir: str) -> None:
        self.export_overlay.complete(
            output_dir, written, failed=self._export_failed)
        self._set_export_busy(False)
        self._last_export_dir = output_dir
        self._teardown_export()

        self._pages["reports"].report_done(written, output_dir)
        self._toasts.show(
            f"Exported {len(written)} report(s) to "
            f"{os.path.basename(output_dir)}",
            "success" if not self._export_failed else "warning")

    def _on_export_failed(self, message: str) -> None:
        self.export_overlay.fail(message)
        self._set_export_busy(False)
        self._teardown_export()
        self._pages["reports"].report_failed(message)
        self._toasts.show(f"Export failed: {message}", "error")

    def _set_export_busy(self, busy: bool) -> None:
        self._pages["reports"].set_busy(busy)
        self.export_btn_top.setEnabled(not busy)

    def _teardown_export(self) -> None:
        """Release the export thread; safe to call when nothing runs."""
        if self._export_thread is not None:
            self._export_thread.quit()
            self._export_thread.wait(3000)
        if self._export_worker is not None:
            self._export_worker.deleteLater()
        if self._export_thread is not None:
            self._export_thread.deleteLater()
        self._export_thread = None
        self._export_worker = None

    def _cancel_export(self) -> None:
        """Request cancellation of the running export."""
        if self._export_worker is not None:
            self._export_worker.cancel()

    def _open_last_export_dir(self) -> None:
        if self._last_export_dir and open_path(self._last_export_dir):
            return
        self._toasts.show("No exported reports yet.", "info")


# ----------------------------------------------------------------------
    # Overlays
    # ----------------------------------------------------------------------

    def _wire_overlays(self) -> None:
        """Create the overlays and connect their actions."""
        self.export_overlay = ExportOverlay(self)
        self.export_overlay.openRequested.connect(
            self._on_open_folder_requested)
        self.export_overlay.backRequested.connect(self._back_to_analysis)
        self.export_overlay.beginRequested.connect(self._retry_export)

        self.shortcuts_overlay = ShortcutsOverlay(self)
        self.theme_overlay = ThemeOverlay(self)
        self.theme_overlay.themePicked.connect(self.manager.set_theme)
        self.theme_overlay.accentPicked.connect(self.manager.set_accent)

        self.confirm_overlay = ConfirmOverlay(self)

        self._pages["reports"].exportRequested.connect(self.start_export)
        self._pages["reports"].openFolderRequested.connect(
            self._on_open_folder_requested)

    def _on_open_folder_requested(self, path: str) -> None:
        """Reveal ``path`` in the OS file manager, reporting the outcome."""
        if open_path(path):
            self._toasts.show("Opened output folder.", "success")
        else:
            self._toasts.show("Could not open that folder.", "error")

    def _back_to_analysis(self) -> None:
        """The explicit escape hatch offered after an export completes."""
        self._goto("overview")
        self._toasts.show("Back to the analysis overview.", "info")

    def _retry_export(self) -> None:
        """Re-run the last export with the same formats and destination."""
        if not self._export_formats or not self._export_dir:
            self._goto("reports")
            return
        self.start_export(self._export_dir, self._export_formats)

    def _show_shortcuts(self) -> None:
        self.shortcuts_overlay.show_sheet()

    def _open_theme_picker(self) -> None:
        self.theme_overlay.show_picker(
            self.manager.tokens.key, self.manager.accent, THEMES, ACCENTS)


# ----------------------------------------------------------------------
    # Shortcuts
    # ----------------------------------------------------------------------

    def _install_shortcuts(self) -> None:
        def bind(seq: str, handler: Callable[[], None]) -> None:
            QShortcut(QKeySequence(seq), self, activated=handler)

        bind("Ctrl+O", self._browse)
        bind("F5", self.start_scan)
        bind("Ctrl+R", self.start_scan)
        bind("Ctrl+L", lambda: self.path_edit.setFocus())
        bind("Ctrl+E", lambda: self._goto("reports"))
        bind("Ctrl+S", self._export_from_page)
        bind("Ctrl+Shift+O", self._open_last_export_dir)
        bind("Ctrl+T", self._toggle_theme)
        bind("Ctrl+,", lambda: self._goto("settings"))
        bind("?", self._show_shortcuts)
        for index in range(9):
            bind(f"Ctrl+{index + 1}",
                 lambda i=index: self._goto_page_index(i))

        self.escape = QShortcut(QKeySequence("Esc"), self)
        self.escape.activated.connect(self._on_escape)

    def _on_escape(self) -> None:
        """Close the topmost overlay, else cancel a scan, else clear toasts."""
        for overlay in (self.export_overlay, self.shortcuts_overlay,
                        self.theme_overlay, self.confirm_overlay):
            if overlay.isVisible():
                if overlay is self.export_overlay and self._export_thread:
                    self._cancel_export()
                overlay.hide_animated()
                return
        if self._thread is not None:
            self.cancel_scan()
            return
        self._toasts.clear()

    def _export_from_page(self) -> None:
        """Ctrl+S: export using whatever the Reports page currently has."""
        self._goto("reports")
        reports = self._pages["reports"]
        self.start_export(reports.output_dir(), reports.selected_formats())

    def _toggle_theme(self) -> None:
        self.manager.toggle_theme()

    # ------------------------------------------------------------------
    # Cross-page plumbing
    # ------------------------------------------------------------------

    def _wire_viewer_callbacks(self) -> None:
        """Let the file tables open selections in the File Viewer page."""
        viewer_page = self._pages["viewer"]

        def open_in_viewer(path: str) -> None:
            viewer_page.open_path(path)
            self._goto("viewer")

        self._pages["explorer"].set_viewer_callback(open_in_viewer)
        self._pages["advanced"].set_viewer_callback(open_in_viewer)

    # ------------------------------------------------------------------
    # Theme reactions
    # ------------------------------------------------------------------

    def _on_theme_changed(self, tokens_obj) -> None:
        """Re-render theme-dependent visuals after a theme/accent switch.

        QtCharts colours are drawn by the charts themselves, outside the reach
        of QSS, so the chart pages are rebuilt from the stored result.
        """
        if self._result is not None and self._result.has_data:
            for key in ("charts", "timeline"):
                self._pages[key].set_result(self._result)
        icon = "sun" if not tokens_obj.dark else "moon"
        color = "#94a3b8" if tokens_obj.dark else "#b45309"
        self.theme_btn.setIcon(get_svg_icon(icon, color=color, size=16))

    # ------------------------------------------------------------------
    # Window events
    # ------------------------------------------------------------------

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        toasts = getattr(self, "_toasts", None)
        if toasts is not None:
            toasts.on_parent_resize()

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._worker is not None:
            self._worker.cancel()
        self._teardown_worker()
        if self._export_worker is not None:
            self._export_worker.cancel()
        self._teardown_export()
        super().closeEvent(event)

    # ------------------------------------------------------------------
    # Backwards-compatible accessors (old tests / external callers)
    # ------------------------------------------------------------------

    @property
    def pages(self) -> List[object]:
        """Page widgets in navigation order (legacy accessor)."""
        return [self._pages[key] for key in PAGE_KEYS]

    @property
    def nav(self) -> QListWidget:
        """The sidebar navigation list (legacy accessor)."""
        assert self._nav is not None
        return self._nav

    @nav.setter
    def nav(self, value: QListWidget) -> None:
        self._nav = value
