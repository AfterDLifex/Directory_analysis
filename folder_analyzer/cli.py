"""
Optional command-line interface.

Lets the same engine run headless (e.g. in CI or over SSH) and produce the
same self-contained reports as the GUI.  Run with:

    python -m folder_analyzer --path "C:\\Users\\me\\Documents" --formats all
    python -m folder_analyzer --path ./data --formats html,json --output ./out

The GUI entry point is ``main.py``; this CLI is a convenience wrapper.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import time
from pathlib import Path
from typing import List

from . import __version__
from .analyzer import FolderAnalyzer
from .exporters import export_csv, export_html, export_json, export_markdown, export_txt
from .models import AnalysisConfig
from .scanner import FolderScanner

FORMAT_MAP = {
    "txt": export_txt,
    "md": export_markdown,
    "json": export_json,
    "csv": export_csv,
    "html": export_html,
}
ALL_FORMATS = list(FORMAT_MAP.keys())


def _is_tty() -> bool:
    return sys.stdout.isatty() and os.environ.get("NO_COLOR", "") == ""


class _C:
    GREEN = "\033[92m" if _is_tty() else ""
    YELLOW = "\033[93m" if _is_tty() else ""
    RED = "\033[91m" if _is_tty() else ""
    CYAN = "\033[96m" if _is_tty() else ""
    BOLD = "\033[1m" if _is_tty() else ""
    END = "\033[0m" if _is_tty() else ""


def _print_summary(result) -> None:
    r = result
    print(f"{_C.BOLD}Folder Storage Analytics{_C.END} v{__version__}")
    print(f"{_C.CYAN}Folder:{_C.END} {r.root_path}")
    print(f"{_C.CYAN}Files:{_C.END} {r.total_files}  "
          f"{_C.CYAN}Folders:{_C.END} {r.total_directories}  "
          f"{_C.CYAN}Storage:{_C.END} {r.total_storage_formatted}  "
          f"{_C.CYAN}Avg:{_C.END} {r.avg_file_size_formatted}")
    if r.duplicate_groups:
        print(f"{_C.YELLOW}Duplicates:{_C.END} {len(r.duplicate_groups)} group(s), "
              f"wasting {_C.RED}{r.duplicate_wasted_formatted}{_C.END}")
    print(f"{_C.BOLD}Key insights:{_C.END}")
    for ins in r.key_insights:
        print(f"  - {ins}")


def main(argv: List[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="folder_analyzer", description="Cross-platform folder storage analytics.")
    p.add_argument("--path", "-p", required=True, help="Folder to analyse.")
    p.add_argument("--output", "-o", default=None,
                   help="Output dir for reports (default: <path>/folder_analysis).")
    p.add_argument("--formats", "-f", default="all",
                   help=f"Comma-separated formats: {','.join(ALL_FORMATS)} or 'all'.")
    p.add_argument("--top", type=int, default=30, help="Top N entries per breakdown.")
    p.add_argument("--no-hidden", action="store_true", help="Skip hidden files/dirs.")
    p.add_argument("--no-duplicates", action="store_true", help="Disable duplicate detection.")
    p.add_argument("--tree-depth", type=int, default=3, help="Directory tree depth.")
    p.add_argument("--quiet", "-q", action="store_true", help="Suppress terminal summary.")
    p.add_argument("--version", action="version", version=f"Folder Analytics {__version__}")
    args = p.parse_args(argv)

    folder = os.path.abspath(args.path)
    if not os.path.isdir(folder):
        print(f"{_C.RED}Error:{_C.END} not a directory: {folder}", file=sys.stderr)
        return 2

    output_dir = args.output or os.path.join(folder, "folder_analysis")
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    formats = ALL_FORMATS if args.formats.strip().lower() == "all" else [
        f.strip() for f in args.formats.split(",") if f.strip() in FORMAT_MAP
    ]
    if not formats:
        print(f"{_C.RED}Error:{_C.END} no valid formats chosen.", file=sys.stderr)
        return 2

    cfg = AnalysisConfig(
        folder_path=folder, top_n=args.top,
        include_hidden=not args.no_hidden,
        detect_duplicates=not args.no_duplicates,
        tree_max_depth=args.tree_depth,
    )

    scanner = FolderScanner(folder, include_hidden=cfg.include_hidden)
    print(f"{_C.CYAN}Scanning {_C.BOLD}{folder}{_C.END} ...")
    t0 = time.perf_counter()
    files = scanner.scan()
    result = FolderAnalyzer(cfg).analyze(
        files, permission_errors=scanner.permission_errors,
        dirs_scanned=scanner.dirs_scanned)
    elapsed = time.perf_counter() - t0

    written = []
    names = {"txt": "SUMMARY.txt", "md": "REPORT.md", "json": "DATA.json",
             "csv": "DATA.csv", "html": "DASHBOARD.html"}
    for fmt in formats:
        out = os.path.join(output_dir, names[fmt])
        FORMAT_MAP[fmt](result, out)
        written.append(out)

    if not args.quiet:
        _print_summary(result)
        print(f"\n{_C.GREEN}Wrote {_C.BOLD}{len(written)}{_C.END} {_C.GREEN}report(s) to:{_C.END} {output_dir}")
        print(f"{_C.CYAN}Elapsed: {elapsed:.1f}s{_C.END}")
    return 0
