"""
Cross-platform folder scanner.

Uses low-level :func:`os.scandir` iteration for speed, respects a
cancellation flag for use inside a GUI worker thread, and tolerates
permission errors so a single unreadable subtree never aborts a whole scan.
It is deliberately I/O-only: no aggregation happens here, which keeps the
scanner testable in isolation.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, List, Optional

from .constants import is_hidden
from .models import FileInfo

ProgressCallback = Callable[[int, int], None]
FileCallback = Callable[[FileInfo], None]


class FolderScanner:
    """Walk a folder tree and emit :class:`FileInfo` records."""

    def __init__(
        self,
        root: str,
        include_hidden: bool = False,
        follow_symlinks: bool = False,
        on_progress: Optional[ProgressCallback] = None,
        on_file: Optional[FileCallback] = None,
    ) -> None:
        self.root = str(Path(root).resolve())
        self.include_hidden = include_hidden
        self.follow_symlinks = follow_symlinks
        self._on_progress = on_progress or (lambda f, d: None)
        self._on_file = on_file or (lambda f: None)
        self._stopped = False

        # statistics from the last run
        self.files_scanned: int = 0
        self.dirs_scanned: int = 0
        self.permission_errors: int = 0
        self.total_bytes: int = 0

    # -- public API ---------------------------------------------------------

    def stop(self) -> None:
        """Request the scan to abort as soon as possible."""
        self._stopped = True

    @property
    def stopped(self) -> bool:
        return self._stopped

    def scan(self) -> List[FileInfo]:
        """Scan the tree and return every file found."""
        self._stopped = False
        self.files_scanned = 0
        self.dirs_scanned = 0
        self.permission_errors = 0
        self.total_bytes = 0

        files: List[FileInfo] = []
        root_path = Path(self.root)
        if not root_path.exists():
            raise FileNotFoundError(f"Folder does not exist: {self.root}")
        if not root_path.is_dir():
            raise NotADirectoryError(f"Not a directory: {self.root}")

        self.dirs_scanned = 0
        stack: List[tuple] = [(str(root_path), 0)]

        while stack and not self._stopped:
            current_str, _depth = stack.pop()
            try:
                with os.scandir(current_str) as it:
                    entries = sorted(it, key=lambda e: e.name)
            except (PermissionError, OSError):
                self.permission_errors += 1
                continue

            self.dirs_scanned += 1
            self._on_progress(self.files_scanned, self.dirs_scanned)

            for entry in entries:
                if self._stopped:
                    break
                try:
                    is_dir = entry.is_dir(follow_symlinks=self.follow_symlinks)
                    is_file = entry.is_file(follow_symlinks=self.follow_symlinks)
                    if not is_dir and not is_file:
                        continue
                    if is_dir:
                        if not self.include_hidden:
                            try:
                                st = entry.stat()
                            except OSError:
                                continue
                            if is_hidden(entry.name, st):
                                continue
                        stack.append((entry.path, _depth + 1))
                    else:
                        self._process_file(entry, files)
                except (PermissionError, OSError):
                    self.permission_errors += 1
                    continue

        self._on_progress(self.files_scanned, self.dirs_scanned)
        return files

    # -- internals ----------------------------------------------------------

    def _process_file(self, entry, files: List[FileInfo]) -> None:
        """Stat-collect a single file entry into a :class:`FileInfo`."""
        try:
            st = entry.stat()
        except (PermissionError, OSError):
            self.permission_errors += 1
            return

        if not self.include_hidden and is_hidden(entry.name, st):
            return

        info = FileInfo(
            path=entry.path,
            name=entry.name,
            parent=str(Path(entry.path).parent),
                        suffix=Path(entry.name).suffix.lower(),
            size=st.st_size,
            modified=st.st_mtime,
        )
        self.files_scanned += 1
        self.total_bytes += info.size
        files.append(info)
        self._on_file(info)
