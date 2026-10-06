"""
Background export worker.

Report generation used to run inline on the GUI thread, which froze the whole
window for the duration of an HTML/JSON export - that is why the app appeared
to hang and users could not click back into the analyser. This worker moves the
write loop onto a ``QThread`` and reports each format as it completes, so the
UI (and the sidebar) stay responsive for the whole export.
"""

from __future__ import annotations

import os
import time
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import QObject, Signal

from folder_analyzer.models import AnalysisResult

#: format key -> (exporter function name, output filename, takes a title)
FORMATS: Dict[str, Tuple[str, str, bool]] = {
    "html": ("export_html", "DASHBOARD.html", True),
    "md": ("export_markdown", "REPORT.md", True),
    "json": ("export_json", "DATA.json", False),
    "csv": ("export_csv", "DATA.csv", False),
    "txt": ("export_txt", "SUMMARY.txt", False),
}

#: Human labels used by the progress overlay.
LABELS: Dict[str, str] = {
    "html": "HTML Dashboard",
    "md": "Markdown Summary",
    "json": "JSON Data",
    "csv": "CSV Breakdown",
    "txt": "Plain Text",
}


def plan(formats: List[str]) -> List[Tuple[str, str, str]]:
    """Turn a format key list into ``(key, label, filename)`` plan rows."""
    return [(key, LABELS[key], FORMATS[key][1]) for key in formats
            if key in FORMATS]


def human_size(num_bytes: int) -> str:
    """Compact byte size for the overlay's per-file detail line."""
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{int(size)} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"


class ExportWorker(QObject):
    """Writes the selected report formats on a worker thread."""

    stageStarted = Signal(int, str)        # index, note
    stageFinished = Signal(int, str)       # index, "FILE · 12.4 KB"
    stageFailed = Signal(int, str)         # index, error text
    progress = Signal(int, int)            # completed, total
    completed = Signal(list, str)          # written paths, output dir
    failed = Signal(str)                    # fatal error (setup)
    elapsedChanged = Signal(float)

    def __init__(self, result: AnalysisResult, formats: List[str],
                 output_dir: str,
                 parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.result = result
        self.formats = [f for f in formats if f in FORMATS]
        self.output_dir = output_dir
        self._cancelled = False
        # Yield to the GUI periodically so the UI stays responsive.
        self._yield_every = 4

    def cancel(self) -> None:
        """Stop before the next format starts."""
        self._cancelled = True

    def _yield_to_ui(self, step: int) -> None:
        """Release the GIL briefly so the GUI thread can repaint.

        The exporters are CPU-bound Python code that holds the GIL for long
        stretches; without an occasional pause the main thread starves and the
        progress overlay stops repainting - users perceive that as a frozen
        export. ``time.sleep`` yields the GIL (``processEvents`` would not,
        and is not safe to call from a worker thread).
        """
        if step % self._yield_every == 0:
            time.sleep(0.004)

    # -- worker entry point ------------------------------------------------

    def run(self) -> None:
        """Executed on the worker thread via ``QThread.started``."""
        if self.result is None or not self.result.has_data:
            self.failed.emit("There is no analysis to export yet — run a scan first.")
            return

        try:
            os.makedirs(self.output_dir, exist_ok=True)
        except OSError as exc:
            self.failed.emit(f"Could not create the output folder: {exc}")
            return

        from folder_analyzer import exporters

        title = self.result.root_name
        written: List[str] = []
        total = len(self.formats)
        started = time.perf_counter()

        for index, key in enumerate(self.formats):
            if self._cancelled:
                break
            func_name, filename, takes_title = FORMATS[key]
            path = os.path.join(self.output_dir, filename)

            self.stageStarted.emit(index, "writing…")
            self._yield_to_ui(index)
            try:
                func = getattr(exporters, func_name)
                if takes_title:
                    func(self.result, path, title=title)
                else:
                    func(self.result, path)
            except Exception as exc:                      # noqa: BLE001
                self.stageFailed.emit(index, str(exc))
                continue

            try:
                detail = f"{filename}  ·  {human_size(os.path.getsize(path))}"
            except OSError:
                detail = filename
            written.append(path)
            self.stageFinished.emit(index, detail)
            self.progress.emit(index + 1, total)
            self.elapsedChanged.emit(round(time.perf_counter() - started, 2))
            self._yield_to_ui(index)

        if self._cancelled:
            self.failed.emit("Export cancelled before all formats were written.")
            return

        self.completed.emit(written, self.output_dir)