"""
Data models for the folder analysis engine.

All models are plain dataclasses so they stay easy to serialise to JSON,
render into tables, or feed into charts. No third-party dependency here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class FileInfo:
    """A single file discovered while scanning a folder tree.

    Kept intentionally lean: only the fields the engine actually needs.
    ``parent`` is the absolute path of the containing directory, used to
    roll file sizes up to their directory.
    """

    path: str          # absolute, OS-native path string
    name: str
    parent: str
    suffix: str        # lower-cased extension including the dot, e.g. ".pdf"
    size: int          # bytes
    modified: float    # epoch seconds (mtime)


@dataclass
class FileRecord:
    """A view of a file ready to be displayed in a table."""

    name: str
    type: str          # human readable type / category
    size: int
    size_formatted: str
    parent: str        # parent directory (shortened for readability)
    modified: float
    modified_formatted: str


@dataclass
class AnalysisConfig:
    """User-facing options for a single analysis run.

    Defaults are deliberately cross-platform and contain *no* hard-coded
    Windows paths so the same config works on Windows, macOS and Linux.
    """

    folder_path: str = ""
    top_n: int = 30

    # scanning behaviour
    include_hidden: bool = False
    follow_symlinks: bool = False
    max_traverse_entries: int = 0  # 0 == no limit

    # duplicate detection
    detect_duplicates: bool = True
    max_duplicate_size_mb: int = 100
    duplicate_hash_algorithm: str = "md5"

    # output / detail
    tree_max_depth: int = 3
    largest_n: int = 50
    oldest_n: int = 50
    generated_at: str = ""

    def __post_init__(self) -> None:
        if self.generated_at:
            # normalise to an ISO-like string
            self.generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class AnalysisResult:
    """Everything the analyzer computes for one folder, in one place."""

    config: AnalysisConfig
    root_path: str
    root_name: str
    generated_at: str

    # headline numbers
    total_files: int = 0
    total_storage: int = 0
    total_directories: int = 0
    total_storage_formatted: str = "0 B"
    avg_file_size: int = 0
    avg_file_size_formatted: str = "0 B"

    # breakdown lists (each entry is a dict for easy templating / charting)
    file_types: List[Dict[str, Any]] = field(default_factory=list)
    top_directories: List[Dict[str, Any]] = field(default_factory=list)
    categories: List[Dict[str, Any]] = field(default_factory=list)
    age_distribution: List[Dict[str, Any]] = field(default_factory=list)
    size_distribution: List[Dict[str, Any]] = field(default_factory=list)
    depth_distribution: List[Dict[str, Any]] = field(default_factory=list)

    # file tables
    largest_files: List[FileRecord] = field(default_factory=list)
    oldest_files: List[FileRecord] = field(default_factory=list)

    # duplicates
    duplicate_groups: List[Dict[str, Any]] = field(default_factory=list)
    duplicate_wasted_bytes: int = 0
    duplicate_wasted_formatted: str = "0 B"

    # textual artefacts
    tree_text: str = ""
    key_insights: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    scan_duration_seconds: float = 0.0

    # convenience
    @property
    def has_data(self) -> bool:
        return self.total_files > 0
