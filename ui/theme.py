"""
Glassmorphic visual theme and styles for Folder Analysis Pro.

Features:
- Glassmorphism: semi-transparent layered surfaces, subtle multi-layer borders,
  vibrant accents, frosted backdrop feel, depth shadows, glowing focus states.
- Clean typography, modern color tokens, polished controls and charts styling.
"""

from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtCore import Qt

# Cross-platform premium font stack
_FONT_STACK = "'Segoe UI', -apple-system, BlinkMacSystemFont, 'Inter', Roboto, Oxygen, Ubuntu, sans-serif"

# Theme Palette Tokens
BG_DARK = "#090d16"
BG_GLASS = "rgba(18, 24, 38, 0.72)"
BG_GLASS_CARD = "rgba(23, 31, 48, 0.65)"
BG_GLASS_HOVER = "rgba(35, 47, 72, 0.80)"
BORDER_GLASS = "rgba(255, 255, 255, 0.08)"
BORDER_GLASS_STRONG = "rgba(110, 168, 254, 0.28)"
ACCENT_PRIMARY = "#4f8cff"
ACCENT_CYAN = "#00d2ff"
ACCENT_PURPLE = "#a855f7"

STYLE_SHEET = f"""
/* ==================== ROOT APPLICATION ==================== */
QMainWindow, QWidget#CentralWidget, QWidget#RootContainer {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #080c14,
        stop:0.45 #0b111e,
        stop:1.0 #080d16);
    color: #e6edf8;
    font-family: {_FONT_STACK};
    font-size: 13px;
}}

/* ==================== TOOLTIPS ==================== */
QToolTip {{
    background: rgba(18, 26, 42, 0.95);
    color: #ffffff;
    border: 1px solid rgba(110, 168, 254, 0.35);
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 12px;
    font-weight: 500;
}}

/* ==================== TOP GLASS HEADER ==================== */
#TopBar {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(14, 20, 34, 0.95),
        stop:0.5 rgba(20, 28, 46, 0.92),
        stop:1 rgba(14, 20, 34, 0.95));
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    padding: 12px 22px;
}}

#AppLogoBadge {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #3b82f6, stop:1 #8b5cf6);
    color: #ffffff;
    font-weight: 800;
    font-size: 13px;
    padding: 6px 12px;
    border-radius: 9px;
    border: 1px solid rgba(255, 255, 255, 0.3);
    letter-spacing: 0.08em;
}}

#TopBarTitle {{
    color: #ffffff;
    font-size: 16px;
    font-weight: 700;
    letter-spacing: 0.2px;
}}

#TopBarSubtitle {{
    color: #8da2c0;
    font-size: 11px;
    font-weight: 500;
}}

/* ==================== SIDEBAR NAVIGATION ==================== */
#NavContainer {{
    background: rgba(11, 16, 28, 0.85);
    border-right: 1px solid rgba(255, 255, 255, 0.07);
}}

#NavList {{
    background: transparent;
    border: none;
    outline: none;
    font-weight: 600;
    font-size: 13px;
    padding: 10px 8px;
}}

#NavList::item {{
    height: 44px;
    margin: 4px 6px;
    padding: 0 14px;
    border-radius: 10px;
    color: #94a3b8;
    background: transparent;
    border: 1px solid transparent;
}}

#NavList::item:hover {{
    background: rgba(255, 255, 255, 0.06);
    color: #ffffff;
    border: 1px solid rgba(255, 255, 255, 0.1);
}}

#NavList::item:selected, #NavList::item:selected:focus {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(59, 130, 246, 0.35),
        stop:1 rgba(139, 92, 246, 0.22));
    color: #ffffff;
    border: 1px solid rgba(96, 165, 250, 0.55);
    font-weight: 700;
}}

/* ==================== GLASS CARDS & PANELS ==================== */
QGroupBox, .GlassCard {{
    background: rgba(18, 25, 42, 0.7);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 14px;
    margin: 8px 0;
    padding: 16px 18px;
    font-weight: 600;
    color: #e2e8f0;
}}

QGroupBox:hover, .GlassCard:hover {{
    border-color: rgba(96, 165, 250, 0.35);
    background: rgba(22, 32, 54, 0.75);
}}

QGroupBox::title {{
    subline-origin: margin;
    subline-offset: 6px;
    padding: 0 8px;
    color: #8da2c0;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}}

/* ==================== STAT CARDS ==================== */
#StatCard {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(28, 38, 60, 0.7),
        stop:1 rgba(16, 22, 36, 0.6));
    border: 1px solid rgba(255, 255, 255, 0.09);
    border-radius: 14px;
    min-height: 80px;
}}

#StatCard:hover {{
    border-color: rgba(96, 165, 250, 0.35);
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(34, 46, 74, 0.75),
        stop:1 rgba(20, 28, 46, 0.65));
}}

#StatCardTitle {{
    color: #8da2c0;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.08em;
}}

#StatCardValue {{
    color: #ffffff;
    font-size: 22px;
    font-weight: 800;
    letter-spacing: -0.5px;
    margin-top: 2px;
}}

#StatCardSub {{
    color: #5d718f;
    font-size: 11px;
    font-weight: 500;
}}

/* ==================== INPUTS & CONTROLS ==================== */
QLineEdit, QComboBox {{
    background: rgba(14, 20, 32, 0.85);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 9px;
    padding: 8px 12px;
    color: #f8fafc;
    font-size: 13px;
    selection-background-color: #3b82f6;
}}

QLineEdit:hover, QComboBox:hover {{
    border-color: rgba(147, 197, 253, 0.35);
    background: rgba(18, 25, 40, 0.9);
}}

QLineEdit:focus, QComboBox:focus {{
    border: 1px solid #3b82f6;
    background: rgba(20, 28, 46, 0.95);
}}

/* ==================== BUTTONS ==================== */
QPushButton {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #2563eb);
    color: #ffffff;
    border: 1px solid rgba(255, 255, 255, 0.18);
    border-radius: 9px;
    padding: 8px 16px;
    font-weight: 600;
    font-size: 13px;
}}

QPushButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #60a5fa, stop:1 #3b82f6);
    border-color: rgba(255, 255, 255, 0.35);
}}

QPushButton:pressed {{
    background: #1d4ed8;
}}

QPushButton:disabled {{
    background: rgba(30, 41, 59, 0.5);
    color: #64748b;
    border: 1px solid rgba(255, 255, 255, 0.04);
}}

#SecondaryButton, #BrowseButton {{
    background: rgba(30, 41, 59, 0.7);
    color: #e2e8f0;
    border: 1px solid rgba(255, 255, 255, 0.10);
}}

#SecondaryButton:hover, #BrowseButton:hover {{
    background: rgba(51, 65, 85, 0.85);
    border-color: rgba(255, 255, 255, 0.22);
    color: #ffffff;
}}

#CancelButton {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ef4444, stop:1 #dc2626);
    border: 1px solid rgba(255, 255, 255, 0.15);
}}

#CancelButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #f87171, stop:1 #ef4444);
}}

#RunButton {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #7c3aed);
    border: 1px solid rgba(255, 255, 255, 0.25);
    font-weight: 700;
    padding: 8px 18px;
}}

#RunButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #8b5cf6);
}}

/* ==================== TABLES & TREES ==================== */
QTableWidget, QTreeWidget {{
    background: rgba(15, 21, 34, 0.75);
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 12px;
    gridline-color: rgba(255, 255, 255, 0.04);
    alternate-background-color: rgba(22, 30, 48, 0.45);
    selection-background-color: rgba(59, 130, 246, 0.35);
    selection-color: #ffffff;
    outline: none;
}}

QHeaderView::section {{
    background: rgba(20, 28, 44, 0.95);
    color: #94a3b8;
    border: none;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    padding: 8px 12px;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}}

QTableWidget::item, QTreeWidget::item {{
    padding: 6px 10px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.02);
}}

QTableWidget::item:hover, QTreeWidget::item:hover {{
    background: rgba(255, 255, 255, 0.04);
}}

/* ==================== CHECKBOXES ==================== */
QCheckBox {{
    color: #e2e8f0;
    spacing: 8px;
    font-size: 13px;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 1px solid rgba(255, 255, 255, 0.18);
    background: rgba(15, 21, 34, 0.8);
}}

QCheckBox::indicator:hover {{
    border-color: #60a5fa;
    background: rgba(24, 34, 54, 0.9);
}}

QCheckBox::indicator:checked {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #3b82f6, stop:1 #2563eb);
    border-color: #60a5fa;
}}

/* ==================== PROGRESS BAR ==================== */
QProgressBar {{
    border: none;
    background: rgba(255, 255, 255, 0.06);
    border-radius: 4px;
    text-align: center;
}}

QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #00d2ff,
        stop:0.5 #3a7bd5,
        stop:1 #8b5cf6);
    border-radius: 4px;
}}

/* ==================== TABS ==================== */
QTabWidget::pane {{
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    background: rgba(17, 23, 37, 0.65);
    top: -1px;
}}

QTabBar::tab {{
    background: rgba(14, 19, 31, 0.7);
    color: #8da2c0;
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-bottom: none;
    border-top-left-radius: 9px;
    border-top-right-radius: 9px;
    padding: 8px 18px;
    margin-right: 4px;
    font-weight: 600;
    font-size: 12px;
}}

QTabBar::tab:selected {{
    background: rgba(23, 31, 48, 0.85);
    color: #ffffff;
    border-color: rgba(96, 165, 250, 0.4);
    border-bottom: 2px solid #3b82f6;
}}

QTabBar::tab:hover:!selected {{
    background: rgba(28, 38, 58, 0.8);
    color: #cbd5e1;
}}

/* ==================== SCROLLBARS ==================== */
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: rgba(255, 255, 255, 0.15);
    min-height: 24px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical:hover {{
    background: rgba(255, 255, 255, 0.28);
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
    background: none;
}}

QScrollBar:horizontal {{
    background: transparent;
    height: 8px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: rgba(255, 255, 255, 0.15);
    min-width: 24px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal:hover {{
    background: rgba(255, 255, 255, 0.28);
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
    background: none;
}}

/* ==================== STATUS BAR ==================== */
#StatusBar {{
    background: rgba(11, 16, 26, 0.90);
    border-top: 1px solid rgba(255, 255, 255, 0.06);
    padding: 6px 18px;
}}
#StatusBar QLabel {{
    color: #94a3b8;
    font-size: 12px;
}}
"""


def apply_theme(app) -> None:
    """Apply the dark glassmorphic palette + stylesheet to a QApplication."""
    palette = QPalette()
    dark = {
        QPalette.ColorRole.Window: "#090d16",
        QPalette.ColorRole.WindowText: "#e6edf8",
        QPalette.ColorRole.Base: "#0e1420",
        QPalette.ColorRole.AlternateBase: "#141c2c",
        QPalette.ColorRole.ToolTipBase: "#121a2a",
        QPalette.ColorRole.ToolTipText: "#ffffff",
        QPalette.ColorRole.Text: "#e6edf8",
        QPalette.ColorRole.Button: "#151d2e",
        QPalette.ColorRole.ButtonText: "#ffffff",
        QPalette.ColorRole.Highlight: "#3b82f6",
        QPalette.ColorRole.HighlightedText: "#ffffff",
        QPalette.ColorRole.PlaceholderText: "#64748b",
    }
    for role, color in dark.items():
        palette.setColor(role, QColor(color))
    palette.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.BrightText, QColor("#ffffff"))
    app.setPalette(palette)
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(STYLE_SHEET)
