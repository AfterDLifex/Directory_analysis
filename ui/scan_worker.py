"""Background scan worker running on a QThread."""

from __future__ import annotations

import time

from PySide6.QtCore import QObject, Signal

from folder_analyzer import FolderAnalyzer, FolderScanner
from folder_analyzer.models import AnalysisConfig, AnalysisResult


class ScanWorker(QObject):
    progressChanged = Signal(int, int)
    finished = Signal(object)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, config: AnalysisConfig, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.config = config
        self._scanner: FolderScanner | None = None
        self._cancelled = False
        self._last_progress_at = 0.0
        self._progress_interval = 0.10

    def run(self) -> None:
        try:
            self._last_progress_at = 0.0
            scanner = FolderScanner(
                self.config.folder_path,
                include_hidden=self.config.include_hidden,
                follow_symlinks=self.config.follow_symlinks,
                on_progress=self._on_progress,
            )
            self._scanner = scanner
            self.progressChanged.emit(0, 0)
            files = scanner.scan()
            if self._cancelled:
                self.cancelled.emit()
                return
            analyzer = FolderAnalyzer(self.config)
            result = analyzer.analyze(
                files,
                permission_errors=scanner.permission_errors,
                dirs_scanned=scanner.dirs_scanned,
            )
            if self._cancelled:
                self.cancelled.emit()
                return
            self.finished.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))

    def cancel(self) -> None:
        self._cancelled = True
        if self._scanner is not None:
            self._scanner.stop()

    def _on_progress(self, files: int, dirs: int) -> None:
        if self._cancelled:
            return
        # FolderScanner calls us for every directory.  Queuing every one of
        # those cross-thread signals can overwhelm Qt's main-event queue on a
        # large project, starving repaint/input even though scanning itself is
        # correctly off the GUI thread.
        now = time.monotonic()
        if now - self._last_progress_at < self._progress_interval:
            return
        self._last_progress_at = now
        self.progressChanged.emit(files, dirs)
