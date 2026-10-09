#!/usr/bin/env python3
"""
Cross-platform build helper: produce a standalone executable.

Usage (from the project root or anywhere):

    python build/build_app.py                 # fast-start folder build
    python build/build_app.py --onefile       # portable single executable
    python build/build_app.py --console       # keep a console for debugging

Works on Windows, macOS and Linux; the output lands in ``dist/``. The default
is a ``FolderAnalysisPro`` application folder (``.exe`` inside it on Windows).
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

# Modules that are never needed by this app -> smaller executable, faster
# startup, and a smaller number of Python modules for PyInstaller to import
# during boot (which is what makes the first visible frame appear late on
# onefile builds).
EXCLUDED = [
    "tkinter",
    "unittest",
    "pydoc_data",
    # WebEngine / browser stack
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebEngineQuick",
    "PySide6.QtWebChannel",
    "PySide6.QtWebSockets",
    # QML / Quick / 3D
    "PySide6.QtQuick",
    "PySide6.QtQuick3D",
    "PySide6.QtQuickWidgets",
    "PySide6.QtQml",
    "PySide6.QtQmlModels",
    "PySide6.Qt3DCore",
    "PySide6.Qt3DRender",
    "PySide6.Qt3DAnimation",
    "PySide6.Qt3DExtras",
    "PySide6.Qt3DInput",
    "PySide6.Qt3DLogic",
    # Peripherals / test tooling
    "PySide6.QtTest",
    "PySide6.QtSql",
    "PySide6.QtDesigner",
    "PySide6.QtHelp",
    "PySide6.QtUiTools",
    "PySide6.QtPositioning",
    "PySide6.QtSerialPort",
    "PySide6.QtSerialBus",
    "PySide6.QtSensors",
    "PySide6.QtRemoteObjects",
    "PySide6.QtScxml",
    "PySide6.QtNetworkAuth",
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


def _pre_clean(root: str, onedir: bool) -> bool:
    """Remove stale build artefacts before PyInstaller runs.

    On Windows, antivirus scanners or a still-running previous build can keep
    a DLL locked.  PyInstaller otherwise fails much later while assembling
    ``COLLECT`` with an unhelpful ``WinError 32``.
    """
    stale = [
        os.path.join(root, "build", APP_NAME),
        os.path.join(
            root, "dist", APP_NAME if onedir
            else APP_NAME + (".exe" if os.name == "nt" else ""),
        ),
    ]
    for path in stale:
        if not os.path.exists(path):
            continue
        if _remove_with_retry(path):
            print(f"Removed stale artefact: {path}")
        else:
            print(
                f"ERROR: could not remove locked build artefact: {path}\n"
                "Close FolderAnalysisPro (and any Explorer preview window), "
                "then run the build again."
            )
            return False
    return True


def build(onedir: bool = True, console: bool = False, keep_workpath: bool = False) -> int:
    """Invoke PyInstaller with the right flags for this platform."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root)

    if shutil.which("pyinstaller") is None and _module_missing():
        print("PyInstaller is not installed.  Run:  pip install pyinstaller")
        return 1

    if not _pre_clean(root, onedir):
        return 1

    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm"]
    if not keep_workpath:
        cmd.append("--clean")
    cmd.append("--onedir" if onedir else "--onefile")
    if not console:
        cmd.append("--windowed")
    # UPX compression adds a decompression step on every launch, which shows
    # up as a longer blank-window period on startup. Skip it - the size gain
    # is not worth the perceived slowness.
    cmd.append("--noupx")
    # Strip docstrings and asserts at package time; harmless for this app and
    # shaves a little off the boot import cost.
    try:
        cmd += ["--optimize", "2"]
    except Exception:
        pass
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
    output = (os.path.join("dist", APP_NAME, APP_NAME + suffix)
              if onedir else os.path.join("dist", APP_NAME + suffix))
    size = os.path.getsize(output) / (1024 * 1024) if os.path.exists(output) else 0
    print(f"\nDone: {output}" + (f"  ({size:.1f} MB)" if size else ""))
    if not onedir:
        print(
            "Note: --onefile extracts every bundled module to a temp folder on "
            "each launch, which is what causes the brief blank-window flicker "
            "before the UI appears. Use --onedir for near-instant startup."
        )
    return 0


def _module_missing() -> bool:
    try:
        import PyInstaller  # noqa: F401
        return False
    except ImportError:
        return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the FolderAnalysisPro executable.")
    layout = parser.add_mutually_exclusive_group()
    layout.add_argument("--onedir", dest="onedir", action="store_true",
                        help="Build an application folder (the default).")
    layout.add_argument("--onefile", dest="onedir", action="store_false",
                        help="Build one portable executable; it starts more slowly.")
    parser.set_defaults(onedir=True)
    parser.add_argument("--console", action="store_true",
                        help="Keep the console window (useful for debugging).")
    parser.add_argument("--keep-workpath", action="store_true",
                        help="Keep PyInstaller's intermediate build directory.")
    args = parser.parse_args()
    return build(onedir=args.onedir, console=args.console,
                 keep_workpath=args.keep_workpath)


if __name__ == "__main__":
    raise SystemExit(main())
