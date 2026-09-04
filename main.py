#!/usr/bin/env python3
"""
Folder Analysis Pro
===================
A modern, cross-platform desktop app for folder storage analytics.

* Interactive GUI (PySide6 / Qt for Python) with live charts
* Duplicate file detection, age & size distributions, categories
* Self-contained report exports (HTML / Markdown / JSON / CSV / TXT)

Usage:
    python main.py                 # launch the GUI
    python -m folder_analyzer -p <folder> --formats all   # headless CLI

Packaging (single-file executable):
    python build/build_app.py      # -> dist/FolderAnalysisPro(.exe)

Author: AfterDLifex
Version: 3.0.0
License: MIT
"""

from __future__ import annotations

import sys


def main() -> int:
    """Create the Qt application, apply the theme and show the window."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QIcon, QPixmap
    from PySide6.QtWidgets import QApplication

    from ui.main_window import MainWindow
    from ui.theme import apply_theme

    app = QApplication(sys.argv)
    app.setApplicationName("Folder Analysis Pro")
    app.setApplicationDisplayName("Folder Analysis Pro")
    app.setOrganizationName("AfterDLifex")

    # High-DPI defaults are on by default in Qt6; just keep crisp text.
    app.setStyle("Fusion")
    apply_theme(app)

    # A simple programmatic app icon (no external asset needed): a rounded
    # indigo tile with a lighter inner square.
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.transparent)
    from PySide6.QtGui import QPainter, QColor
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("#5684e2"))
    painter.drawRoundedRect(2, 2, 60, 60, 14, 14)
    painter.setBrush(QColor("#8fb3ff"))
    painter.drawRoundedRect(16, 16, 32, 32, 8, 8)
    painter.end()
    app.setWindowIcon(QIcon(pixmap))

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
