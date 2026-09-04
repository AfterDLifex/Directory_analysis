"""
Background scan worker.

Runs the (potentially slow) folder scan + analysis off the GUI thread so the
interface stays responsive, and streams progress back through Qt signals.
Cancellation is cooperative: the worker forwards ``cancel()`` to the
scanner, which aborts its walk as soon as possible.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from folder_analyzer import FolderAnalyzer, FolderScanner
from folder_analyzer.models import AnalysisConfig, AnalysisResult


class ScanWorker(QObject):
    """Scan + analyse a folder in a background thread."""

    progressChanged = Signal(int, int)   # files scanned, directories scanned
    finished = Signal(object)            # AnalysisResult
    failed = Signal(str)                 # error message
    cancelled = Signal()

    def __init__(self, config: AnalysisConfig, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.config = config
        self._scanner: FolderScanner | None = None
        self._cancelled = False

    # -- slots ---------------------------------------------------------------

    def run(self) -> None:
        """Perform the scan + analysis (called on the worker thread)."""
        try:
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
        except Exception as exc:  # pragma: no cover - surfaced to the GUI
            self.failed.emit(str(exc))

    def cancel(self) -> None:
        """Request cancellation of the running scan."""
        self._cancelled = True
        if self._scanner is not None:
            self._scanner.stop()

    # -- internals ------------------------------------------------------------

    def _on_progress(self, files: int, dirs: int) -> None:
        if not self._cancelled:
            self.progressChanged.emit(files, dirs)
