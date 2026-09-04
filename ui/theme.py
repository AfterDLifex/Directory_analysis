"""
Visual theme for the GUI.

A hand-written dark "material" stylesheet + palette.  No external assets are
used, so the look is identical on Windows, macOS and Linux.
"""

from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtCore import Qt


# A cross-platform font stack via stylesheet; Qt falls back gracefully.
_FONT_STACK = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, " \
              "Oxygen, Ubuntu, Helvetica, Arial, sans-serif"


STYLE_SHEET = f"""
/* ---- root ---- */
QMainWindow {{
    background: #0b0f16;
    color: #e6e6e6;
    font-family: {_FONT_STACK};
    font-size: 13px;
}}
QToolTip {{
    background: #252b36;
    color: #e6e6e6;
    border: 1px solid #444c60;
    border-radius: 6px;
    padding: 4px 8px;
}}

/* ---- top bar ---- */
#TopBar {{
    background: #121823;
    border-bottom: 1px solid #212a3d;
    padding: 12px 16px;
}}
#TopBar QLabel {{ color: #9aa3b8; }}

/* ---- sidebar navigation ---- */
#NavList {{
    background: #121823;
    border-right: 1px solid #212a3d;
    outline: none;
    font-weight: 500;
}}
#NavList::item {{
    padding: 12px 16px;
    border-left: 3px solid transparent;
}}
#NavList::item:selected, #NavList::item:selected:focus {{
    background: #1b2538;
    border-left: 3px solid #5684e2;
    color: #ffffff;
}}
#NavList::item:hover {{
    background: #1b2538;
    border-left: 3px solid #3b4455;
}}

/* ---- cards / panels ---- */
QGroupBox {{
    background: #171e2e;
    border: 1px solid #25304a;
    border-radius: 12px;
    margin: 12px 0;
    padding: 14px 16px;
    font-weight: 600;
    color: #cdd6e6;
}}
QGroupBox::title {{
    subline-offset: 0;
    padding: 0 6px;
    color: #9aa3b8;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}}

/* ---- controls ---- */
QLineEdit, QComboBox {{
    background: #1e273d;
    border: 1px solid #2d3a53;
    border-radius: 8px;
    padding: 7px 10px;
    color: #e6e6e6;
}}
QLineEdit:focus, QComboBox:focus {{
    border-color: #5684e2;
}}
QPushButton {{
    background: #5684e2;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 8px 14px;
    font-weight: 600;
}}
QPushButton:hover {{ background: #6a91f2; }}
QPushButton:pressed {{ background: #436bd1; }}
QPushButton:disabled {{ background: #3b4455; color: #6b7280; }}
#CancelButton {{ background: #e6495b; }}
#CancelButton:hover {{ background: #f25a6d; }}
#RunButton[running="true"] {{ background: #0f62a3; }}

/* ---- tables / trees ---- */
QTableWidget, QTreeWidget {{
    background: #171e2e;
    border: 1px solid #25304a;
    border-radius: 10px;
    gridline-color: #25304a;
    alternate-background-color: #1a2130;
    selection-background-color: #2b3a5e;
}}
QHeaderView::section {{
    background: #212a3d;
    color: #9aa3b8;
    border: none;
    padding: 6px 10px;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}}
QHeaderView {{ background: transparent; }}

/* ---- progress ---- */
QProgressBar {{
    border: none;
    background: transparent;
    text-align: center;
}}
QProgressBar::chunk {{
    background: #5684e2;
    border-radius: 4px;
}}

/* ---- tabs ---- */
QTabWidget::pane {{
    border: 1px solid #25304a;
    border-radius: 10px;
    background: #171e2e;
}}
QTabBar::tab {{
    background: #212a3d;
    color: #9aa3b8;
    border: 1px solid #25304a;
    border-bottom: none;
    border-top-left: 8px;
    border-top-right: 8px;
    padding: 8px 14px;
    margin: 0 -1px;
    border-bottom: 1px solid transparent;
}}
QTabBar::tab:selected {{
    background: #171e2e;
    color: #ffffff;
    border-color: #25304a;
    border-bottom: 2px solid #5684e2;
}}
QTabBar::tab:hover {{ background: #2a3750; }}
"""


def apply_theme(app) -> None:
    """Apply the dark material palette + stylesheet to a QApplication."""
    palette = QPalette()
    dark = {
        QPalette.ColorRole.Window: "#0b0f16",
        QPalette.ColorRole.WindowText: "#e6e6e6",
        QPalette.ColorRole.Base: "#171e2e",
        QPalette.ColorRole.AlternateBase: "#1a2130",
        QPalette.ColorRole.ToolTipBase: "#252b36",
        QPalette.ColorRole.ToolTipText: "#e6e6e6",
        QPalette.ColorRole.Text: "#e6e6e6",
        QPalette.ColorRole.Button: "#171e2e",
        QPalette.ColorRole.ButtonText: "#e6e6e6",
        QPalette.ColorRole.Highlight: "#5684e2",
        QPalette.ColorRole.HighlightedText: "#ffffff",
        QPalette.ColorRole.PlaceholderText: "#6b7280",
    }
    for role, color in dark.items():
        palette.setColor(role, QColor(color))
    palette.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.BrightText, QColor("#ffffff"))
    app.setPalette(palette)
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(STYLE_SHEET)
