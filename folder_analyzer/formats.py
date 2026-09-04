"""
Formatting and hashing helpers.

All functions here are pure (no I/O on global state) so they are trivial to
unit-test and reuse from both the GUI and the CLI exporter.
"""

from __future__ import annotations

import hashlib
import os
from datetime import datetime
from typing import Optional


# ---------------------------------------------------------------------------
# Human readable sizes / numbers
# ---------------------------------------------------------------------------

_SIZE_UNITS = ("B", "KB", "MB", "GB", "TB", "PB", "EB")


def format_size(size_bytes: float) -> str:
    """Format a byte count into a compact, locale-independent string."""
    if size_bytes is None:
        return "0 B"
    size = float(size_bytes)
    if size < 0:
        return "-" + format_size(-size_bytes)
    if size == 0:
        return "0 B"
    unit_index = 0
    value = size
    while value >= 1024 and unit_index < len(_SIZE_UNITS) - 1:
        value /= 1024.0
        unit_index += 1
    if unit_index == 0:
        return f"{int(value)} {_SIZE_UNITS[unit_index]}"
    return f"{value:.2f} {_SIZE_UNITS[unit_index]}"


def format_number(num: Optional[int]) -> str:
    """Format an integer with thousands separators."""
    if num is None:
        return "0"
    return f"{num:,}"


def format_percentage(value: float, total: float, digits: int = 2) -> float:
    """Return a percentage value; 0 when the total is zero."""
    if total <= 0:
        return 0.0
    return round((value / total) * 100.0, digits)


def format_timestamp(epoch: float) -> str:
    """Format an epoch timestamp into a readable date/time string."""
    try:
        return datetime.fromtimestamp(epoch).strftime("%Y-%m-%d %H:%M:%S")
    except (OSError, ValueError, OverflowError):
        return "Unknown"


# ---------------------------------------------------------------------------
# Hashing used for duplicate detection.
# ---------------------------------------------------------------------------

# Only read this many bytes when *sampling* huge files; for full hashing we
# still stream the whole file but stop early past the configured cap.
_HASH_CHUNK = 1024 * 1024  # 1 MiB read chunks


def hash_file(path: str, algorithm: str = "md5", max_bytes: Optional[int] = None) -> str:
    """Stream-hash a file, optionally stopping after ``max_bytes``.

    Reading is chunked so even large files stay memory-friendly.  When a
    cap is supplied and the file is larger we still read up to the cap
    (enough to distinguish non-identical files) and append a sentinel.
    """
    h = hashlib.new(algorithm)
    cap_reached = False
    try:
        with open(path, "rb") as fh:
            if max_bytes is None:
                for chunk in iter(lambda: fh.read(_HASH_CHUNK), b""):
                    h.update(chunk)
            else:
                remaining = max_bytes
                while remaining > 0:
                    chunk = fh.read(min(_HASH_CHUNK, remaining))
                    if not chunk:
                        break
                    h.update(chunk)
                    remaining -= len(chunk)
                # If there is more data we intentionally do not read it, but we
                # append a length marker so two files truncated at the cap are
                # still distinguishable when their sizes differ.
                if fh.read(1):
                    cap_reached = True
    except (OSError, PermissionError):
        # Unreadable file -> empty hash; it will never match another file.
        return ""
    digest = h.hexdigest()
    if cap_reached:
        digest += f":{os.path.getsize(path)}"
    return digest
