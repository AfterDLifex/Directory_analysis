"""
Shared constants: file-type categories, age/size buckets, colour palettes
and small icon/helpers that are pure-Python and therefore fully portable.

Nothing here depends on an operating system beyond ``sys.platform`` checks,
so the same file is used by the scanner, analyzer and exporters.
"""

from __future__ import annotations

import sys
from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------
# File-type categories.  Mapping is data-driven so it is trivial to extend.
# ---------------------------------------------------------------------------

# (category name, display colour used in charts)
_CATEGORY_COLORS: List[Tuple[str, str]] = [
    ("Images", "#FF6B6B"),
    ("Videos", "#4ECDC4"),
    ("Documents", "#45B7D1"),
    ("Audio", "#96CEB4"),
    ("Archives", "#FECA57"),
    ("Code", "#FF9FF3"),
    ("Executables", "#ADB5BD"),
    ("Fonts", "#54A0FF"),
    ("System", "#5F2DA0"),
    ("Other", "#6BCB77"),
]

# ext -> category lookup, built from the list above + explicit entries.
_EXT_MAP: Dict[str, str] = {
    # Images
    ".jpg": "Images", ".jpeg": "Images", ".png": "Images", ".gif": "Images",
    ".bmp": "Images", ".svg": "Images", ".webp": "Images", ".ico": "Images",
    ".tiff": "Images", ".tif": "Images", ".heic": "Images", ".heif": "Images",
    # Videos
    ".mp4": "Videos", ".mov": "Videos", ".avi": "Videos", ".mkv": "Videos",
    ".wmv": "Videos", ".flv": "Videos", ".webm": "Videos", ".m4v": "Videos",
    ".3gp": "Videos", ".webm": "Videos",
    # Audio
    ".mp3": "Audio", ".wav": "Audio", ".flac": "Audio", ".aac": "Audio",
    ".ogg": "Audio", ".m4a": "Audio", ".wma": "Audio", ".opus": "Audio",
    # Documents
    ".pdf": "Documents", ".doc": "Documents", ".docx": "Documents",
    ".txt": "Documents", ".rtf": "Documents", ".odt": "Documents",
    ".ppt": "Documents", ".pptx": "Documents", ".xls": "Documents",
    ".xlsx": "Documents", ".csv": "Documents", ".md": "Documents",
    ".pages": "Documents", ".key": "Documents", ".numbers": "Documents",
    ".odp": "Documents", ".ods": "Documents",
    # Archives
    ".zip": "Archives", ".rar": "Archives", ".7z": "Archives", ".tar": "Archives",
    ".gz": "Archives", ".tgz": "Archives", ".bz2": "Archives", ".xz": "Archives",
    ".lz": "Archives", ".iso": "Archives",
    # Code
    ".py": "Code", ".js": "Code", ".ts": "Code", ".jsx": "Code", ".tsx": "Code",
    ".html": "Code", ".htm": "Code", ".css": "Code", ".scss": "Code",
    ".sass": "Code", ".less": "Code", ".json": "Code", ".xml": "Code",
    ".yaml": "Code", ".yml": "Code", ".java": "Code", ".c": "Code",
    ".cpp": "Code", ".cc": "Code", ".h": "Code", ".hpp": "Code",
    ".cs": "Code", ".go": "Code", ".rs": "Code", ".rb": "Code",
    ".php": "Code", ".sql": "Code", ".sh": "Code", ".vue": "Code",
    ".svelte": "Code", ".cmake": "Code",
    # Executables
    ".exe": "Executables", ".msi": "Executables", ".app": "Executables",
    ".com": "Executables", ".bin": "Executables", ".jar": "Executables",
    ".deb": "Executables", ".rpm": "Executables",
    # Libraries / system
    ".dll": "System", ".so": "System", ".dylib": "System", ".sys": "System",
    ".ko": "System",
    # Fonts
    ".ttf": "Fonts", ".otf": "Fonts", ".woff": "Fonts", ".woff2": "Fonts",
    ".eot": "Fonts", ".fon": "Fonts",
}

CATEGORY_COLORS: Dict[str, str] = {
    name: color for name, color in _CATEGORY_COLORS
}
CATEGORY_ORDER: List[str] = [name for name, _ in _CATEGORY_COLORS]


def get_file_category(suffix: str) -> str:
    """Return the human category for a file extension."""
    return _EXT_MAP.get(suffix.lower(), "Other")


# ---------------------------------------------------------------------------
# Size buckets for the size-distribution analysis.
# (label, lower_inclusive, upper_exclusive)
# ---------------------------------------------------------------------------

SIZE_BUCKETS: List[Tuple[str, float, float]] = [
    ("< 1 KB", 0, 1024),
    ("1 KB - 1 MB", 1024, 1024 ** 2),
    ("1 MB - 10 MB", 1024 ** 2, 10 * 1024 ** 2),
    ("10 MB - 100 MB", 10 * 1024 ** 2, 100 * 1024 ** 2),
    ("100 MB - 1 GB", 100 * 1024 ** 2, 1024 ** 3),
    ("> 1 GB", 1024 ** 3, float("inf")),
]


# ---------------------------------------------------------------------------
# Age buckets, measured in days relative to the scan time.
# ---------------------------------------------------------------------------

AGE_BUCKETS: List[Tuple[str, float, float]] = [
    ("Last 7 days", 0, 7),
    ("7 - 30 days", 7, 30),
    ("30 - 90 days", 30, 90),
    ("90 - 365 days", 90, 365),
    ("1 - 2 years", 365, 730),
    ("Older than 2 years", 730, float("inf")),
]


# ---------------------------------------------------------------------------
# Colour palettes reused for charts & the HTML report.
# ---------------------------------------------------------------------------

COLOR_PALETTES: Dict[str, List[str]] = {
    "gradient": [
        "#667eea", "#764ba2", "#f093fb", "#f5576c", "#4facfe",
    ],
    "vibrant": [
        "#FF6B6B", "#4ECDC4", "#FFE66D", "#6B5B95", "#FF9F43",
        "#B5347B", "#F77F00",
    ],
    "pastel": [
        "#FFB3BA", "#BAFFC9", "#BAE1FF", "#FFFFBA", "#FFBFDE",
        "#B5EAFF", "#E0BBE4", "#FFC9DE",
    ],
    "neon": [
        "#FF006E", "#00F0FF", "#F6FF40", "#FF00FF", "#00FF9D",
        "#00FFEA",
    ],
}


def get_color(index: int, palette: str = "gradient") -> str:
    """Return a deterministic colour from a palette."""
    colors = COLOR_PALETTES.get(palette, COLOR_PALETTES["gradient"])
    return colors[index % len(colors)]


# ---------------------------------------------------------------------------
# Small icon (emoji) helpers for tables and the tree view.
# Pure text -> no image assets, fully cross-platform.
# ---------------------------------------------------------------------------

_CATEGORY_ICONS: Dict[str, str] = {
    "Images": "🖼️",
    "Videos": "🎬",
    "Documents": "📄",
    "Audio": "🎵",
    "Archives": "📦",
    "Code": "</>",
    "Executables": "⚙️",
    "Fonts": "🔤",
    "System": "💾",
    "Other": "📎",
}


def get_file_icon(suffix: str) -> str:
    """Return a small icon string for a file extension."""
    return _CATEGORY_ICONS.get(get_file_category(suffix), "📎")


def get_category_icon(category: str) -> str:
    """Return the icon for a category name (e.g. 'Images')."""
    return _CATEGORY_ICONS.get(category, "📎")


def get_dir_icon() -> str:
    return "📁"


# ---------------------------------------------------------------------------
# Cross-platform "is this entry hidden?" helper used by the scanner.
# ---------------------------------------------------------------------------

_WINDOWS = sys.platform.startswith("win")


def is_hidden(name: str, stat_result) -> bool:
    """Return True if a filesystem entry is hidden on the current OS.

    * Unix-like: leading dot in the name.
    * Windows: ``FILE_ATTRIBUTE_HIDDEN`` bit (via ``st_file_attributes``).
    """
    if name.startswith("."):
        return True
    if _WINDOWS:
        attr = getattr(stat_result, "st_file_attributes", 0)
        try:
            import stat as _stat
            if attr & _stat.FILE_ATTRIBUTE_HIDDEN:
                return True
        except Exception:
            pass
    return False
