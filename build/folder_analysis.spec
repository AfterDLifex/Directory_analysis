# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Folder Analysis Pro.

Build with:   pyinstaller build/folder_analysis.spec --noconfirm --clean
(or simply use the friendlier wrapper:  python build/build_app.py)

Single-file, windowed application; works on Windows, macOS and Linux.
"""
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = (
    collect_submodules("folder_analyzer")
    + collect_submodules("ui")
    + ["PySide6.QtCharts", "PySide6.QtSvg"]
)

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtQuick3D",
        "PySide6.Qt3DCore",
        "PySide6.QtTest",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="FolderAnalysisPro",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
