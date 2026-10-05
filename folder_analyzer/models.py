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
    """A single file discovered while scanning a folder tree."""

    path: str
    name: str
    parent: str
    suffix: str
    size: int
    modified: float


@dataclass
class FileRecord:
    """A view of a file ready to be displayed in a table."""

    name: str
    type: str
    size: int
    size_formatted: str
    parent: str
    modified: float
    modified_formatted: str
    path: str = ""
    ext: str = ""


@dataclass
class AnalysisConfig:
    """User-facing options for a single analysis run."""

    folder_path: str = ""
    top_n: int = 30

    # scanning behaviour
    include_hidden: bool = False
    follow_symlinks: bool = False
    max_traverse_entries: int = 0

    # duplicate detection
    detect_duplicates: bool = True
    max_duplicate_size_mb: int = 100
    duplicate_hash_algorithm: str = "md5"

    # output / detail
    tree_max_depth: int = 3
    largest_n: int = 50
    oldest_n: int = 50
    recent_n: int = 50
    deep_depth_threshold: int = 6
    junk_min_age_days: int = 30
    generated_at: str = ""

    def __post_init__(self) -> None:
        if self.generated_at:
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

    # storage health & actionable efficiency analysis
    storage_efficiency_score: int = 100
    storage_health_label: str = "Optimal"
    actionable_savings_bytes: int = 0
    actionable_savings_formatted: str = "0 B"
    empty_files_count: int = 0
    empty_files_list: List[Dict[str, Any]] = field(default_factory=list)

    # breakdown lists
    file_types: List[Dict[str, Any]] = field(default_factory=list)
    top_directories: List[Dict[str, Any]] = field(default_factory=list)
    categories: List[Dict[str, Any]] = field(default_factory=list)
    age_distribution: List[Dict[str, Any]] = field(default_factory=list)
    size_distribution: List[Dict[str, Any]] = field(default_factory=list)
    depth_distribution: List[Dict[str, Any]] = field(default_factory=list)

    # -------- NEW: richer analytics --------
    modified_timeline: List[Dict[str, Any]] = field(default_factory=list)
    day_of_week_distribution: List[Dict[str, Any]] = field(default_factory=list)
    hour_of_day_distribution: List[Dict[str, Any]] = field(default_factory=list)
    filename_duplicates: List[Dict[str, Any]] = field(default_factory=list)
    potential_junk: List[Dict[str, Any]] = field(default_factory=list)
    deep_files: List[Dict[str, Any]] = field(default_factory=list)
    extensionless_files: List[Dict[str, Any]] = field(default_factory=list)
    long_path_files: List[Dict[str, Any]] = field(default_factory=list)
    non_ascii_files: List[Dict[str, Any]] = field(default_factory=list)
    mime_summary: List[Dict[str, Any]] = field(default_factory=list)
    directory_children: List[Dict[str, Any]] = field(default_factory=list)

    # file tables
    largest_files: List[FileRecord] = field(default_factory=list)
    oldest_files: List[FileRecord] = field(default_factory=list)
    recent_files: List[FileRecord] = field(default_factory=list)

    # duplicates
    duplicate_groups: List[Dict[str, Any]] = field(default_factory=list)
    duplicate_wasted_bytes: int = 0
    duplicate_wasted_formatted: str = "0 B"

    # textual artefacts & recommendations
    tree_text: str = ""
    key_insights: List[str] = field(default_factory=list)
    actionable_recommendations: List[Dict[str, str]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    scan_duration_seconds: float = 0.0

    @property
    def has_data(self) -> bool:
        return self.total_files > 0