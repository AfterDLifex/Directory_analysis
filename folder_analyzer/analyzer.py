"""
Folder analysis engine.

Given a list of :class:`FileInfo` records (produced by the scanner), the
:class:`FolderAnalyzer` builds a single :class:`AnalysisResult` containing
every aggregate the GUI and exporters need: file-type / category / age /
size / depth breakdowns, top directories, largest & oldest files,
duplicate groups, a text tree and a list of human key-insights.

The engine is pure-Python and side-effect free apart from hashing, so it can
be unit-tested without any GUI.
"""

from __future__ import annotations

import os
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from .constants import (
    AGE_BUCKETS,
    CATEGORY_COLORS,
    CATEGORY_ORDER,
    COLOR_PALETTES,
    SIZE_BUCKETS,
    get_category_icon,
    get_color,
    get_dir_icon,
    get_file_category,
    get_file_icon,
)
from .formats import format_number, format_percentage, format_size, format_timestamp, hash_file
from .models import AnalysisConfig, AnalysisResult, FileInfo


class FolderAnalyzer:
    """Compute a full :class:`AnalysisResult` from a list of files."""

    def __init__(self, config: AnalysisConfig) -> None:
        self.config = config
        self.root = Path(config.folder_path).resolve()
        self.files: List[FileInfo] = []
        self.result: AnalysisResult = self._blank_result()
        self._permission_errors = 0
        self._dirs_scanned = 0

    # -- public API ---------------------------------------------------------

    def analyze(
        self,
        files: List[FileInfo],
        permission_errors: int = 0,
        dirs_scanned: int = 0,
    ) -> AnalysisResult:
        """Run every aggregation and return the populated result."""
        start = time.perf_counter()
        self.files = list(files)
        self._permission_errors = permission_errors
        self._dirs_scanned = dirs_scanned
        cfg = self.config
        self.result = self._blank_result()

        if not self.files:
            self._finalize(start)
            return self.result

        total_bytes = sum(f.size for f in self.files)
        total_files = len(self.files)
        self.result.total_files = total_files
        self.result.total_storage = total_bytes
        self.result.total_storage_formatted = format_size(total_bytes)
        self.result.avg_file_size = int(total_bytes // total_files) if total_files else 0
        self.result.avg_file_size_formatted = format_size(self.result.avg_file_size)
        self.result.total_directories = dirs_scanned or self._count_directories()

        self.result.file_types = self._file_types()
        self.result.top_directories = self._top_directories(cfg.top_n)
        self.result.categories = self._categories()
        self.result.age_distribution = self._age_distribution(datetime.now().timestamp())
        self.result.size_distribution = self._size_distribution()
        self.result.depth_distribution = self._depth_distribution()
        self.result.largest_files = self._top_files(cfg.largest_n, sort_key=lambda f: f.size, reverse=True)
        self.result.oldest_files = self._top_files(cfg.oldest_n, sort_key=lambda f: f.modified, reverse=False)

        if cfg.detect_duplicates:
            self._detect_duplicates()
        self.result.duplicate_wasted_formatted = format_size(
            self.result.duplicate_wasted_bytes)

        self.result.tree_text = self._build_tree()
        self.result.key_insights = self._build_insights()
        self._finalize(start)
        return self.result

    # -- helpers ------------------------------------------------------------

    def _blank_result(self) -> AnalysisResult:
        return AnalysisResult(
            config=self.config,
            root_path=str(self.root),
            root_name=self.root.name or str(self.root),
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

    def _count_directories(self) -> int:
        return len({f.parent for f in self.files})

    def _short_parent(self, parent: str) -> str:
        """Shorten a parent path relative to the root for display."""
        try:
            rel = Path(parent).relative_to(self.root)
            if str(rel) == ".":
                return self.root.name
            return self.root.name + "/" + str(rel)
        except ValueError:
            return parent

    def _file_types(self) -> List[Dict]:
        palette = COLOR_PALETTES["gradient"]
        groups: Dict[str, List[FileInfo]] = defaultdict(list)
        for f in self.files:
            groups[f.suffix or "(no ext)"].append(f)
        total = self.result.total_storage
        rows = []
        for ext, files in sorted(groups.items(), key=lambda kv: sum(x.size for x in kv[1]), reverse=True):
            size = sum(f.size for f in files)
            rows.append({
                "type": ext,
                "label": ext if ext != "(no ext)" else "(no extension)",
                "files": len(files),
                "size": size,
                "size_formatted": format_size(size),
                "percentage": format_percentage(size, total),
                "category": get_file_category(ext),
                "icon": get_file_icon(ext),
                "color": palette[len(rows) % len(palette)],
            })
        return rows

    def _top_directories(self, n: int) -> List[Dict]:
        groups: Dict[str, List[FileInfo]] = defaultdict(list)
        for f in self.files:
            groups[f.parent].append(f)
        total = self.result.total_storage
        rows = []
        for parent, files in sorted(groups.items(), key=lambda kv: sum(x.size for x in kv[1]), reverse=True)[:n]:
            size = sum(f.size for f in files)
            rows.append({
                "name": self._short_parent(parent),
                "path": parent,
                "files": len(files),
                "size": size,
                "size_formatted": format_size(size),
                "percentage": format_percentage(size, total),
                "color": get_color(len(rows), "gradient"),
            })
        return rows

    def _categories(self) -> List[Dict]:
        groups: Dict[str, List[FileInfo]] = defaultdict(list)
        for f in self.files:
            groups[get_file_category(f.suffix)].append(f)
        total = self.result.total_storage
        rows = []
        for name in CATEGORY_ORDER:
            files = groups.get(name)
            if not files:
                continue
            size = sum(f.size for f in files)
            rows.append({
                "name": name,
                "files": len(files),
                "size": size,
                "size_formatted": format_size(size),
                "percentage": format_percentage(size, total),
                "color": CATEGORY_COLORS.get(name, "#888888"),
                "icon": get_category_icon(name),
            })
        rows.sort(key=lambda r: r["size"], reverse=True)
        return rows

    def _to_record(self, f: FileInfo) -> Dict:
        return {
            "name": f.name,
            "path": f.path,
            "parent": self._short_parent(f.parent),
            "ext": f.suffix,
            "type": get_file_category(f.suffix) if f.suffix else "Other",
            "size": f.size,
            "size_formatted": format_size(f.size),
            "modified": f.modified,
            "modified_formatted": format_timestamp(f.modified),
            "icon": get_file_icon(f.suffix),
        }

    def _top_files(self, n: int, sort_key, reverse: bool) -> List[Dict]:
        ordered = sorted(self.files, key=sort_key, reverse=reverse)[:n]
        return [self._to_record(f) for f in ordered]

    def _detect_duplicates(self) -> None:
        cfg = self.config
        cap_bytes = cfg.max_duplicate_size_mb * 1024 * 1024
        by_size: Dict[int, List[FileInfo]] = defaultdict(list)
        for f in self.files:
            by_size[f.size].append(f)

        for size, files in by_size.items():
            if len(files) < 2:
                continue
            if size == 0:
                self._store_duplicate_group(files, 0, "(empty)")
                continue
            if size > cap_bytes:
                self.result.warnings.append(
                    f"Skipped {len(files)} file(s) of {format_size(size)} each "
                    f"for duplicate detection (>{cfg.max_duplicate_size_mb}MB)."
                )
                continue
            by_hash: Dict[str, List[FileInfo]] = defaultdict(list)
            for f in files:
                digest = hash_file(f.path, cfg.duplicate_hash_algorithm, max_bytes=cap_bytes)
                if digest:
                    by_hash[digest].append(f)
            for members in by_hash.values():
                if len(members) > 1:
                    self._store_duplicate_group(members, size, members[0].path)

    def _store_duplicate_group(self, members: List[FileInfo], size: int, digest: str) -> None:
        wasted = members[0].size * (len(members) - 1)
        self.result.duplicate_wasted_bytes += wasted
        self.result.duplicate_groups.append({
            "hash": digest,
            "size": size,
            "size_formatted": format_size(size),
            "count": len(members),
            "wasted": wasted,
            "wasted_formatted": format_size(wasted),
            "files": [self._to_record(m) for m in members],
            "color": get_color(len(self.result.duplicate_groups), "vibrant"),
        })

    def _build_tree(self) -> str:
        max_depth = self.config.tree_max_depth
        root = self.root
        lines: List[str] = [get_dir_icon() + " " + root.name + "/"]
        try:
            entries = sorted(os.listdir(root))
        except OSError:
            return "\n".join(lines)

        dirs = [e for e in entries if (root / e).is_dir(follow_symlinks=False)]
        files = [e for e in entries if (root / e).is_file(follow_symlinks=False)]
        for d in dirs[: max_depth * 5]:
            lines.append("  " + get_dir_icon() + " " + d + "/")
        for fn in files[:5]:
            lines.append("  " + get_file_icon(fn) + " " + fn)
        if len(files) > 5:
            lines.append(f"  ... and {len(files) - 5} more files")
        return "\n".join(lines)
    def _build_insights(self) -> List[str]:
        r = self.result
        insights: List[str] = []
        if r.file_types:
            top = r.file_types[0]
            insights.append(
                f"**{top['label']}** files consume the most space: "
                f"{top['size_formatted']} ({top['percentage']}% of total)"
            )
        if r.top_directories:
            top = r.top_directories[0]
            insights.append(
                f"**{top['name']}** is the largest directory with "
                f"{top['size_formatted']} ({top['percentage']}% of total)"
            )
        if r.categories:
            top = r.categories[0]
            insights.append(
                f"**{top['name']}** is the dominant category with "
                f"{top['size_formatted']} ({top['percentage']}% of total)"
            )
        if r.age_distribution:
            oldest = max(r.age_distribution, key=lambda x: x["size"])
            insights.append(
                f"Most storage is occupied by files **{oldest['category']}** "
                f"({oldest['size_formatted']})"
            )
        if r.duplicate_groups:
            insights.append(
                f"**{r.duplicate_wasted_formatted}** could be recovered by "
                f"removing {len(r.duplicate_groups)} duplicate group(s)"
            )
        insights.append(f"Average file size is **{r.avg_file_size_formatted}**")
        if self._permission_errors:
            insights.append(
                f"{self._permission_errors} folder(s) were skipped "
                f"due to permission errors."
            )
        return insights

    def _finalize(self, start: float) -> None:
        self.result.scan_duration_seconds = round(time.perf_counter() - start, 2)
        self.result.duplicate_wasted_formatted = format_size(self.result.duplicate_wasted_bytes)
        if self._permission_errors:
            self.result.warnings.append(
                f"{self._permission_errors} folder(s) could not be read "
                f"(permission denied)."
            )

    def _age_distribution(self, now_ts: float) -> List[Dict]:
        total = self.result.total_storage
        counts = {b[0]: 0 for b in AGE_BUCKETS}
        sizes = {b[0]: 0 for b in AGE_BUCKETS}
        for f in self.files:
            age_days = (now_ts - f.modified) / 86400.0
            for label, low, high in AGE_BUCKETS:
                if low <= age_days < high:
                    counts[label] += 1
                    sizes[label] += f.size
                    break
        rows = []
        for label, low, high in AGE_BUCKETS:
            size = sizes[label]
            rows.append({
                "category": label,
                "files": counts[label],
                "size": size,
                "size_formatted": format_size(size),
                "percentage": format_percentage(size, total),
                "color": get_color(len(rows), "vibrant"),
            })
        return rows

    def _size_distribution(self) -> List[Dict]:
        total = self.result.total_files
        counts = {b[0]: 0 for b in SIZE_BUCKETS}
        for f in self.files:
            for label, low, high in SIZE_BUCKETS:
                if low <= f.size < high:
                    counts[label] += 1
                    break
        rows = []
        for label, low, high in SIZE_BUCKETS:
            count = counts[label]
            rows.append({
                "range": label,
                "count": count,
                "percentage": format_percentage(count, total, 1),
                "color": get_color(len(rows), "pastel"),
            })
        return rows

    def _depth_distribution(self) -> List[Dict]:
        counts: Counter = Counter()
        for f in self.files:
            try:
                rel = Path(f.path).relative_to(self.root)
                depth = len(rel.parts) - 1 if rel.parts else 0
            except ValueError:
                depth = 0
            counts[depth] += 1
        total = self.result.total_files
        return [
            {"depth": d, "files": c, "percentage": format_percentage(c, total, 1),
             "color": get_color(d, "neon")}
            for d, c in sorted(counts.items())
        ]


