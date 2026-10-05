"""
Folder analysis engine.

Given a list of :class:`FileInfo` records the :class:`FolderAnalyzer` builds
a single :class:`AnalysisResult` containing every aggregate the GUI and
exporters need. Includes richer analytics: temporal trends, filename
duplication, junk detection, deep nesting, long paths, and more.

Pure-Python and side-effect free apart from hashing.
"""

from __future__ import annotations

import os
import re
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
from .formats import (
    format_number,
    format_percentage,
    format_size,
    format_timestamp,
    hash_file,
)
from .models import AnalysisConfig, AnalysisResult, FileInfo


# Patterns that look like temporary / cache / backup files.
_JUNK_PATTERNS = re.compile(
    r"(?:^~\$|~$|\.tmp$|\.temp$|\.bak$|\.old$|\.orig$|\.swp$|\.swo$|"
    r"\.crdownload$|\.part$|\.partial$|\.download$|\.log\.\d+$|"
    r"\.DS_Store$|Thumbs\.db$|desktop\.ini$|\.cache$)",
    re.IGNORECASE,
)

# Extensions that are typically compressible (text-based).
_TEXT_EXTENSIONS = {
    ".txt", ".log", ".md", ".csv", ".tsv", ".json", ".xml", ".yaml", ".yml",
    ".html", ".htm", ".css", ".js", ".ts", ".py", ".rb", ".go", ".rs",
    ".java", ".c", ".cpp", ".h", ".hpp", ".cs", ".php", ".sh", ".sql",
    ".ini", ".cfg", ".conf", ".toml",
}


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

        # Core breakdowns
        self.result.file_types = self._file_types()
        self.result.top_directories = self._top_directories(cfg.top_n)
        self.result.categories = self._categories()
        self.result.age_distribution = self._age_distribution(datetime.now().timestamp())
        self.result.size_distribution = self._size_distribution()
        self.result.depth_distribution = self._depth_distribution()

        # File tables
        self.result.largest_files = self._top_files(
            cfg.largest_n, sort_key=lambda f: f.size, reverse=True)
        self.result.oldest_files = self._top_files(
            cfg.oldest_n, sort_key=lambda f: f.modified, reverse=False)
        self.result.recent_files = self._top_files(
            cfg.recent_n, sort_key=lambda f: f.modified, reverse=True)

        # Extended analytics (new)
        self.result.modified_timeline = self._modified_timeline()
        self.result.day_of_week_distribution = self._day_of_week_distribution()
        self.result.hour_of_day_distribution = self._hour_of_day_distribution()
        self.result.filename_duplicates = self._filename_duplicates()
        self.result.potential_junk = self._potential_junk()
        self.result.deep_files = self._deep_files(cfg.deep_depth_threshold)
        self.result.extensionless_files = self._extensionless_files()
        self.result.long_path_files = self._long_path_files()
        self.result.non_ascii_files = self._non_ascii_files()
        self.result.mime_summary = self._mime_summary()
        self.result.directory_children = self._directory_children()

        # Duplicates
        if cfg.detect_duplicates:
            self._detect_duplicates()
        self.result.duplicate_wasted_formatted = format_size(
            self.result.duplicate_wasted_bytes)

        self.result.empty_files_list = self._find_empty_files()
        self.result.empty_files_count = len(self.result.empty_files_list)

        self.result.tree_text = self._build_tree()
        self.result.key_insights = self._build_insights()
        self._compute_health_and_recommendations()
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
        try:
            rel = Path(parent).relative_to(self.root)
            if str(rel) == ".":
                return self.root.name
            return self.root.name + "/" + str(rel)
        except ValueError:
            return parent

    def _to_record(self, f: FileInfo) -> Dict:
        return {
            "name": f.name,
            "path": f.path,
            "parent": self._short_parent(f.parent),
            "parent_full": f.parent,
            "ext": f.suffix,
            "type": get_file_category(f.suffix) if f.suffix else "Other",
            "size": f.size,
            "size_formatted": format_size(f.size),
            "modified": f.modified,
            "modified_formatted": format_timestamp(f.modified),
            "icon": get_file_icon(f.suffix),
        }

    # -- core breakdowns ---------------------------------------------------

    def _file_types(self) -> List[Dict]:
        palette = COLOR_PALETTES["gradient"]
        groups: Dict[str, List[FileInfo]] = defaultdict(list)
        for f in self.files:
            groups[f.suffix or "(no ext)"].append(f)
        total = self.result.total_storage
        rows = []
        for ext, files in sorted(groups.items(),
                                 key=lambda kv: sum(x.size for x in kv[1]),
                                 reverse=True):
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
        for parent, files in sorted(groups.items(),
                                    key=lambda kv: sum(x.size for x in kv[1]),
                                    reverse=True)[:n]:
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

    def _top_files(self, n: int, sort_key, reverse: bool) -> List[Dict]:
        ordered = sorted(self.files, key=sort_key, reverse=reverse)[:n]
        return [self._to_record(f) for f in ordered]

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

    # -- NEW analytics -----------------------------------------------------

    def _modified_timeline(self) -> List[Dict]:
        """Files grouped by (year-month), last 24 months shown."""
        buckets: Dict[str, Dict] = {}
        for f in self.files:
            try:
                dt = datetime.fromtimestamp(f.modified)
            except (OSError, ValueError, OverflowError):
                continue
            key = dt.strftime("%Y-%m")
            bucket = buckets.setdefault(key, {"month": key, "files": 0, "size": 0})
            bucket["files"] += 1
            bucket["size"] += f.size

        rows = sorted(buckets.values(), key=lambda r: r["month"])[-24:]
        total = self.result.total_storage or 1
        for i, r in enumerate(rows):
            r["size_formatted"] = format_size(r["size"])
            r["percentage"] = format_percentage(r["size"], total)
            r["color"] = get_color(i, "gradient")
        return rows

    def _day_of_week_distribution(self) -> List[Dict]:
        names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        buckets = {n: {"day": n, "files": 0, "size": 0} for n in names}
        for f in self.files:
            try:
                dt = datetime.fromtimestamp(f.modified)
            except (OSError, ValueError, OverflowError):
                continue
            idx = dt.weekday()
            buckets[names[idx]]["files"] += 1
            buckets[names[idx]]["size"] += f.size
        rows = [buckets[n] for n in names]
        total = self.result.total_storage or 1
        for i, r in enumerate(rows):
            r["size_formatted"] = format_size(r["size"])
            r["percentage"] = format_percentage(r["size"], total)
            r["color"] = get_color(i, "vibrant")
        return rows

    def _hour_of_day_distribution(self) -> List[Dict]:
        buckets = {h: {"hour": h, "files": 0, "size": 0} for h in range(24)}
        for f in self.files:
            try:
                dt = datetime.fromtimestamp(f.modified)
            except (OSError, ValueError, OverflowError):
                continue
            buckets[dt.hour]["files"] += 1
            buckets[dt.hour]["size"] += f.size
        rows = [buckets[h] for h in range(24)]
        total = self.result.total_storage or 1
        for i, r in enumerate(rows):
            r["size_formatted"] = format_size(r["size"])
            r["percentage"] = format_percentage(r["size"], total)
            r["color"] = get_color(i, "neon")
        return rows

    def _filename_duplicates(self) -> List[Dict]:
        """Files sharing the same name but (potentially) different content."""
        by_name: Dict[str, List[FileInfo]] = defaultdict(list)
        for f in self.files:
            by_name[f.name.lower()].append(f)
        rows = []
        for name, files in by_name.items():
            if len(files) < 2:
                continue
            # Only surface those whose content differs (different parent dirs)
            parents = {f.parent for f in files}
            if len(parents) < 2:
                continue
            total = sum(f.size for f in files)
            rows.append({
                "name": files[0].name,
                "count": len(files),
                "size": total,
                "size_formatted": format_size(total),
                "files": [self._to_record(f) for f in files[:10]],
                "color": get_color(len(rows), "vibrant"),
            })
        rows.sort(key=lambda r: r["size"], reverse=True)
        return rows[:100]

    def _potential_junk(self) -> List[Dict]:
        """Temp / cache / backup files older than configurable threshold."""
        cfg = self.config
        min_age = cfg.junk_min_age_days * 86400.0
        now = datetime.now().timestamp()
        rows = []
        for f in self.files:
            is_junk = bool(_JUNK_PATTERNS.search(f.name))
            age_days = (now - f.modified) / 86400.0
            if is_junk and age_days >= cfg.junk_min_age_days:
                rec = self._to_record(f)
                rec["age_days"] = round(age_days)
                rows.append(rec)
        rows.sort(key=lambda r: r["size"], reverse=True)
        return rows[:200]

    def _deep_files(self, threshold: int) -> List[Dict]:
        rows = []
        for f in self.files:
            try:
                rel = Path(f.path).relative_to(self.root)
                depth = len(rel.parts) - 1
            except ValueError:
                continue
            if depth >= threshold:
                rec = self._to_record(f)
                rec["depth"] = depth
                rows.append(rec)
        rows.sort(key=lambda r: (-r["depth"], -r["size"]))
        return rows[:200]

    def _extensionless_files(self) -> List[Dict]:
        rows = [self._to_record(f) for f in self.files if not f.suffix]
        rows.sort(key=lambda r: r["size"], reverse=True)
        return rows[:100]

    def _long_path_files(self, limit: int = 240) -> List[Dict]:
        rows = []
        for f in self.files:
            if len(f.path) >= limit:
                rec = self._to_record(f)
                rec["path_len"] = len(f.path)
                rows.append(rec)
        rows.sort(key=lambda r: -r["path_len"])
        return rows[:100]

    def _non_ascii_files(self) -> List[Dict]:
        rows = []
        for f in self.files:
            try:
                f.name.encode("ascii")
            except UnicodeEncodeError:
                rows.append(self._to_record(f))
        rows.sort(key=lambda r: r["name"])
        return rows[:100]

    def _mime_summary(self) -> List[Dict]:
        """Rough MIME-style summary grouped by top-level type."""
        groups: Dict[str, Dict] = {}
        for f in self.files:
            cat = get_file_category(f.suffix)
            mime = {
                "Images": "image/*", "Videos": "video/*",
                "Audio": "audio/*", "Documents": "application/document",
                "Archives": "application/archive", "Code": "text/*",
                "Executables": "application/executable",
                "Fonts": "font/*", "System": "application/octet-stream",
                "Other": "application/octet-stream",
            }.get(cat, "application/octet-stream")
            bucket = groups.setdefault(
                mime, {"mime": mime, "files": 0, "size": 0, "category": cat})
            bucket["files"] += 1
            bucket["size"] += f.size
        total = self.result.total_storage or 1
        rows = sorted(groups.values(), key=lambda r: -r["size"])
        for i, r in enumerate(rows):
            r["size_formatted"] = format_size(r["size"])
            r["percentage"] = format_percentage(r["size"], total)
            r["color"] = get_color(i, "pastel")
        return rows

    def _directory_children(self) -> List[Dict]:
        """Directories by child count (direct files only)."""
        groups: Dict[str, List[FileInfo]] = defaultdict(list)
        for f in self.files:
            groups[f.parent].append(f)
        rows = []
        for parent, files in groups.items():
            rows.append({
                "name": self._short_parent(parent),
                "path": parent,
                "children": len(files),
                "size": sum(f.size for f in files),
                "size_formatted": format_size(sum(f.size for f in files)),
            })
        rows.sort(key=lambda r: -r["children"])
        return rows[:100]

    # -- duplicate detection ----------------------------------------------

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
                digest = hash_file(f.path, cfg.duplicate_hash_algorithm,
                                   max_bytes=cap_bytes)
                if digest:
                    by_hash[digest].append(f)
            for members in by_hash.values():
                if len(members) > 1:
                    self._store_duplicate_group(members, size, members[0].path)

    def _store_duplicate_group(self, members: List[FileInfo], size: int,
                               digest: str) -> None:
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

    # -- tree / insights / health -----------------------------------------

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
        if r.filename_duplicates:
            insights.append(
                f"**{len(r.filename_duplicates)}** filename collision(s) "
                f"detected across different folders"
            )
        if r.potential_junk:
            junk_size = sum(j["size"] for j in r.potential_junk)
            insights.append(
                f"**{len(r.potential_junk)}** temporary/cache file(s) "
                f"({format_size(junk_size)}) detected — consider cleanup"
            )
        if r.deep_files:
            insights.append(
                f"**{len(r.deep_files)}** deeply nested file(s) beyond depth "
                f"{self.config.deep_depth_threshold}"
            )
        if r.long_path_files:
            insights.append(
                f"**{len(r.long_path_files)}** file path(s) exceed 240 "
                f"characters — may cause issues on some platforms"
            )
        if r.extensionless_files:
            insights.append(
                f"**{len(r.extensionless_files)}** extension-less file(s) "
                f"found — may be scripts, configs or unknowns"
            )
        insights.append(f"Average file size is **{r.avg_file_size_formatted}**")
        if self._permission_errors:
            insights.append(
                f"{self._permission_errors} folder(s) were skipped "
                f"due to permission errors."
            )
        return insights

    def _find_empty_files(self) -> List[Dict]:
        empty = [self._to_record(f) for f in self.files if f.size == 0]
        return empty[:200]

    def _compute_health_and_recommendations(self) -> None:
        r = self.result
        score = 100
        recs = []

        dup_waste = r.duplicate_wasted_bytes
        total_bytes = r.total_storage or 1
        dup_pct = (dup_waste / total_bytes) * 100

        if dup_pct > 25:
            score -= 30
            recs.append({
                "type": "Critical",
                "title": f"Deduplicate Clustered Files ({r.duplicate_wasted_formatted} recoverable)",
                "action": f"Remove {len(r.duplicate_groups)} duplicate clusters to reclaim {r.duplicate_wasted_formatted} of wasted storage."
            })
        elif dup_pct > 10:
            score -= 15
            recs.append({
                "type": "Warning",
                "title": f"Review Redundant Files ({r.duplicate_wasted_formatted} waste)",
                "action": f"{len(r.duplicate_groups)} duplicate file groups detected. Reclaim up to {r.duplicate_wasted_formatted}."
            })
        elif dup_waste > 0:
            score -= 5
            recs.append({
                "type": "Notice",
                "title": "Minor Duplication Detected",
                "action": f"{r.duplicate_wasted_formatted} can be recovered by pruning {len(r.duplicate_groups)} duplicated item(s)."
            })

        # Empty files penalty
        empty_count = r.empty_files_count
        if empty_count > 50:
            score -= 15
            recs.append({
                "type": "Notice",
                "title": f"Clean Up {empty_count:,} Zero-Byte Files",
                "action": "Numerous 0-byte orphan files detected. Cleaning them up simplifies directory indexes."
            })
        elif empty_count > 10:
            score -= 5
            recs.append({
                "type": "Notice",
                "title": f"Orphan 0-Byte Files Found ({empty_count})",
                "action": "Consider removing zero-byte placeholder files to maintain a tidy filesystem."
            })

        # Junk files
        if r.potential_junk:
            junk_size = sum(j["size"] for j in r.potential_junk)
            if junk_size > 50 * 1024 * 1024:
                score -= 10
                recs.append({
                    "type": "Warning",
                    "title": f"Remove {len(r.potential_junk)} Temp/Cache Files",
                    "action": f"Roughly {format_size(junk_size)} of old temporary, cache, or backup files found. Safe to remove in most cases."
                })
            elif junk_size > 5 * 1024 * 1024:
                score -= 4
                recs.append({
                    "type": "Notice",
                    "title": f"Clean Up Temporary Files ({format_size(junk_size)})",
                    "action": "Several old cache/backup files detected. Removing them tidies the folder."
                })

        # Deep nesting
        if len(r.deep_files) > 100:
            score -= 5
            recs.append({
                "type": "Notice",
                "title": f"Deeply Nested Structure ({len(r.deep_files)} files)",
                "action": f"Many files live at depth > {self.config.deep_depth_threshold}. Flattening improves scan and navigation speed."
            })

        # Long paths (Windows MAX_PATH risk)
        if r.long_path_files:
            score -= 5
            recs.append({
                "type": "Warning",
                "title": f"{len(r.long_path_files)} Long Path(s) Detected",
                "action": "Some paths exceed 240 characters. On Windows this may break tools that don't support long paths."
            })

        # Stale/archival files
        old_bucket = next((b for b in r.age_distribution
                           if "Older than" in b["category"]), None)
        if old_bucket and old_bucket["percentage"] > 35:
            score -= 10
            recs.append({
                "type": "Archive",
                "title": f"Archive Stale Data ({old_bucket['size_formatted']} > 2 yrs old)",
                "action": f"{old_bucket['percentage']}% of storage hasn't been touched in over 2 years. Offloading to cold storage saves primary disk."
            })

        # Top heavy directory
        if r.top_directories and r.top_directories[0]["percentage"] > 60:
            top_dir = r.top_directories[0]
            recs.append({
                "type": "Notice",
                "title": f"Storage Imbalance in '{top_dir['name']}'",
                "action": f"Single directory holds {top_dir['percentage']}% of total storage ({top_dir['size_formatted']}). Consider partitioning or organizing subfolders."
            })

        # Top 5 concentration
        if r.largest_files and len(r.largest_files) >= 5:
            top5_sum = sum(f["size"] for f in r.largest_files[:5])
            if (top5_sum / total_bytes) > 0.40 and total_bytes > 50 * 1024 * 1024:
                recs.append({
                    "type": "Notice",
                    "title": "Top 5 Large Files Hold Major Footprint",
                    "action": f"The 5 largest files account for {format_percentage(top5_sum, total_bytes)}% of storage. Review them in File Explorer."
                })

        score = max(10, min(100, score))
        r.storage_efficiency_score = score
        if score >= 90:
            r.storage_health_label = "Optimal"
        elif score >= 75:
            r.storage_health_label = "Good"
        elif score >= 50:
            r.storage_health_label = "Needs Optimization"
        else:
            r.storage_health_label = "High Waste Detected"

        r.actionable_savings_bytes = dup_waste
        r.actionable_savings_formatted = r.duplicate_wasted_formatted
        r.actionable_recommendations = recs

    def _finalize(self, start: float) -> None:
        self.result.scan_duration_seconds = round(time.perf_counter() - start, 2)
        self.result.duplicate_wasted_formatted = format_size(
            self.result.duplicate_wasted_bytes)
        if self._permission_errors:
            self.result.warnings.append(
                f"{self._permission_errors} folder(s) could not be read "
                f"(permission denied)."
            )