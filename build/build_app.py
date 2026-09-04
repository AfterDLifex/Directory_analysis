#!/usr/bin/env python3
"""
Cross-platform build helper: produce a standalone executable.

Usage (from the project root or anywhere):

    python build/build_app.py                 # single-file, windowed
    python build/build_app.py --onedir        # faster-start folder build
    python build/build_app.py --console       # keep a console for debugging

Works on Windows, macOS and Linux; the output lands in ``dist/`` and is
named ``FolderAnalysisPro`` (``.exe`` on Windows).
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
import time

APP_NAME = "FolderAnalysisPro"
ENTRY_POINT = "main.py"

# Qt modules pulled in explicitly so the packager never misses them.
QT_HIDDEN_IMPORTS = ["PySide6.QtCharts", "PySide6.QtSvg"]

# Modules that are never needed by this app -> smaller executable.
EXCLUDED = [
    "tkinter",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtQuick3D",
    "PySide6.Qt3DCore",
    "PySide6.QtTest",
]


def _remove_with_retry(path: str, attempts: int = 5, delay: float = 1.0) -> bool:
    """Delete *path*, retrying briefly (antivirus may transiently lock files)."""
    for i in range(attempts):
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            return True
        except (PermissionError, OSError):
            time.sleep(delay * (i + 1))
    return False


def _pre_clean(root: str) -> None:
    """Remove stale build artefacts before PyInstaller runs.

    On Windows, antivirus scanners can keep a just-written ``.exe`` locked for
    a few seconds, which makes PyInstaller's own ``--clean`` step crash with
    ``PermissionError``.  Deleting (or, as a last resort, renaming aside) the
    artefacts up front avoids that.
    """
    stale = [
        os.path.join(root, "build", APP_NAME),
        os.path.join(root, "dist", APP_NAME + (".exe" if os.name == "nt" else "")),
    ]
    for path in stale:
        if not os.path.exists(path):
            continue
        if _remove_with_retry(path):
            print(f"Removed stale artefact: {path}")
        else:
            aside = path + ".stale-%d" % int(time.time())
            try:
                os.rename(path, aside)
                print(f"Locked file moved aside: {path} -> {aside}")
            except OSError as exc:
                print(f"WARNING: could not clear {path} ({exc}); "
                      "the build may fail on a locked file.")


def build(onedir: bool = False, console: bool = False, keep_workpath: bool = False) -> int:
    """Invoke PyInstaller with the right flags for this platform."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root)

    if shutil.which("pyinstaller") is None and _module_missing():
        print("PyInstaller is not installed.  Run:  pip install pyinstaller")
        return 1

    _pre_clean(root)

    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm"]
    if not keep_workpath:
        cmd.append("--clean")
    cmd.append("--onedir" if onedir else "--onefile")
    if not console:
        cmd.append("--windowed")
    cmd += ["--name", APP_NAME, "--specpath", "build"]
    for mod in QT_HIDDEN_IMPORTS:
        cmd += ["--hidden-import", mod]
    for mod in EXCLUDED:
        cmd += ["--exclude-module", mod]
    cmd.append(ENTRY_POINT)

    print("Building with:\n  " + " ".join(cmd))
    completed = subprocess.run(cmd, check=False)
    if completed.returncode != 0:
        print("Build failed.")
        return completed.returncode

    suffix = ".exe" if platform.system() == "Windows" else ""
    output = os.path.join("dist", APP_NAME + suffix)
    size = os.path.getsize(output) / (1024 * 1024) if os.path.exists(output) else 0
    print(f"\nDone: {output}" + (f"  ({size:.1f} MB)" if size else ""))
    return 0


def _module_missing() -> bool:
    try:
        import PyInstaller  # noqa: F401
        return False
    except ImportError:
        return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the FolderAnalysisPro executable.")
    parser.add_argument("--onedir", action="store_true",
                        help="Build an application folder instead of a single file.")
    parser.add_argument("--console", action="store_true",
                        help="Keep the console window (useful for debugging).")
    parser.add_argument("--keep-workpath", action="store_true",
                        help="Keep PyInstaller's intermediate build directory.")
    args = parser.parse_args()
    return build(onedir=args.onedir, console=args.console,
                 keep_workpath=args.keep_workpath)


if __name__ == "__main__":
    raise SystemExit(main())
