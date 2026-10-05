"""
Glassmorphic visual theme and design tokens for Folder Analysis Pro.

Design language:
- Layered glass surfaces with multi-stop gradients and border highlighting.
- Vibrant accent hues with a consistent cyan -> blue -> violet ramp.
- Precise radii, spacing and typography scales.
- Focus states, hover states and disabled states defined for every control.
"""

from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtCore import Qt

# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------

FONT_FAMILY = ("'Segoe UI', -apple-system, BlinkMacSystemFont, 'Inter', "
               "Roboto, Oxygen, Ubuntu, 'Helvetica Neue', sans-serif")
MONO_FAMILY = ("'JetBrains Mono', 'SFMono-Regular', Consolas, 'Liberation Mono', "
               "Menlo, Monaco, monospace")

# Surfaces
BG_ROOT_STOPS = ("#070b13", "#0a1120", "#070c16")
BG_GLASS = "rgba(18, 24, 38, 0.72)"
BG_GLASS_CARD = "rgba(23, 31, 48, 0.65)"
BG_GLASS_HOVER = "rgba(35, 47, 72, 0.80)"
BG_ELEVATED = "rgba(28, 38, 60, 0.85)"

# Borders
BORDER_SUBTLE = "rgba(255, 255, 255, 0.06)"
BORDER_GLASS = "rgba(255, 255, 255, 0.09)"
BORDER_STRONG = "rgba(110, 168, 254, 0.38)"

# Accents
ACCENT_PRIMARY = "#3b82f6"
ACCENT_BLUE = "#4f8cff"
ACCENT_CYAN = "#00d2ff"
ACCENT_PURPLE = "#a855f7"
ACCENT_VIOLET = "#8b5cf6"
ACCENT_GREEN = "#22c55e"
ACCENT_AMBER = "#f59e0b"
ACCENT_RED = "#ef4444"

# Text
TEXT_PRIMARY = "#e6edf8"
TEXT_MUTED = "#8da2c0"
TEXT_DIM = "#5d718f"
TEXT_FAINT = "#475569"

# Spacing / radius scale
RADIUS_SM = 8
RADIUS_MD = 12
RADIUS_LG = 16
RADIUS_XL = 20


STYLE_SHEET = f"""
/* ==========================================================================
   ROOT APPLICATION
   ========================================================================== */
QWidget {{
    color: {TEXT_PRIMARY};
    font-family: {FONT_FAMILY};
    font-size: 13px;
    outline: none;
}}

QMainWindow, QWidget#CentralWidget, QWidget#RootContainer {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {BG_ROOT_STOPS[0]},
        stop:0.45 {BG_ROOT_STOPS[1]},
        stop:1.0 {BG_ROOT_STOPS[2]});
}}

QWidget#PageRoot, QStackedWidget > QWidget {{
    background: transparent;
}}

QToolTip {{
    background: rgba(12, 18, 30, 0.98);
    color: #ffffff;
    border: 1px solid {BORDER_STRONG};
    border-radius: 8px;
    padding: 6px 11px;
    font-size: 12px;
    font-weight: 500;
}}

/* ==========================================================================
   TOP COMMAND BAR
   ========================================================================== */
#TopBar {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(15, 21, 34, 0.96),
        stop:1 rgba(11, 16, 27, 0.98));
    border-bottom: 1px solid {BORDER_SUBTLE};
}}

#AppLogoBadge {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {ACCENT_PRIMARY}, stop:1 {ACCENT_VIOLET});
    color: #ffffff;
    font-weight: 800;
    font-size: 11px;
    padding: 5px 10px;
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.28);
    letter-spacing: 0.14em;
}}

#TopBarTitle {{
    color: #ffffff;
    font-size: 15px;
    font-weight: 700;
    letter-spacing: 0.2px;
}}

#TopBarSubtitle {{
    color: {TEXT_MUTED};
    font-size: 11px;
    font-weight: 500;
}}

#TopBarSeparator {{
    background: {BORDER_SUBTLE};
    max-width: 1px;
    min-width: 1px;
}}

#CrumbLabel {{
    color: {TEXT_MUTED};
    font-size: 12px;
    font-weight: 500;
}}

#CrumbPath {{
    color: #cbd5e1;
    font-size: 12px;
    font-weight: 600;
    padding: 4px 10px;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid {BORDER_SUBTLE};
    border-radius: 8px;
}}

#KbdHint {{
    color: {TEXT_FAINT};
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.06em;
    padding: 2px 6px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid {BORDER_SUBTLE};
    border-radius: 4px;
}}

/* ==========================================================================
   SIDEBAR
   ========================================================================== */
#NavContainer {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(8, 12, 22, 0.94),
        stop:1 rgba(11, 16, 28, 0.88));
    border-right: 1px solid {BORDER_SUBTLE};
}}

#NavSectionLabel {{
    color: {TEXT_FAINT};
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 0.16em;
    padding: 16px 16px 6px 16px;
}}

#NavList {{
    background: transparent;
    border: none;
    outline: none;
    font-weight: 600;
    font-size: 13px;
    padding: 4px 10px;
}}

#NavList::item {{
    height: 40px;
    margin: 2px 4px;
    padding: 0 12px;
    border-radius: 10px;
    color: #94a3b8;
    background: transparent;
    border: 1px solid transparent;
}}

#NavList::item:hover {{
    background: rgba(255, 255, 255, 0.055);
    color: #ffffff;
    border: 1px solid {BORDER_SUBTLE};
}}

#NavList::item:selected, #NavList::item:selected:focus {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(59, 130, 246, 0.32),
        stop:1 rgba(139, 92, 246, 0.18));
    color: #ffffff;
    border: 1px solid rgba(96, 165, 250, 0.55);
    font-weight: 700;
}}

/* Sidebar quick-stat strip */
#SidebarStat {{
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid {BORDER_SUBTLE};
    border-radius: 10px;
    padding: 10px 12px;
    margin: 2px 10px;
}}
#SidebarStatLabel {{
    color: {TEXT_FAINT};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.1em;
}}
#SidebarStatValue {{
    color: #ffffff;
    font-size: 15px;
    font-weight: 700;
}}

/* ==========================================================================
   PANELS AND CARDS
   ========================================================================== */
QFrame#GlassPanel {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(22, 30, 48, 0.72),
        stop:1 rgba(14, 20, 34, 0.68));
    border: 1px solid {BORDER_GLASS};
    border-radius: {RADIUS_LG}px;
}}

QFrame#GlassPanel:hover {{
    border-color: rgba(110, 168, 254, 0.22);
}}

QLabel#PanelTitle {{
    color: #ffffff;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.02em;
}}

QLabel#PanelSubtitle {{
    color: {TEXT_DIM};
    font-size: 11px;
    font-weight: 500;
}}

QLabel#PanelBadge {{
    color: #cbd5e1;
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid {BORDER_SUBTLE};
    border-radius: 999px;
    padding: 2px 9px;
    font-size: 11px;
    font-weight: 700;
}}

QGroupBox {{
    background: transparent;
    border: 1px solid {BORDER_GLASS};
    border-radius: {RADIUS_LG}px;
    margin: 8px 0 0 0;
    padding: 18px;
    font-weight: 600;
    color: {TEXT_PRIMARY};
}}

QGroupBox::title {{
    subline-origin: margin;
    subline-offset: 8px;
    padding: 0 8px;
    color: {TEXT_MUTED};
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.10em;
}}

/* ==========================================================================
   STAT CARDS
   ========================================================================== */
QFrame#StatCard {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(28, 38, 60, 0.68),
        stop:1 rgba(15, 21, 36, 0.72));
    border: 1px solid {BORDER_GLASS};
    border-radius: 14px;
    min-height: 96px;
}}

QFrame#StatCard:hover {{
    border-color: rgba(96, 165, 250, 0.4);
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(36, 48, 76, 0.75),
        stop:1 rgba(20, 28, 46, 0.72));
}}

QFrame#StatCard[accent="cyan"]   {{ border-top: 2px solid {ACCENT_CYAN}; }}
QFrame#StatCard[accent="blue"]   {{ border-top: 2px solid {ACCENT_BLUE}; }}
QFrame#StatCard[accent="violet"] {{ border-top: 2px solid {ACCENT_VIOLET}; }}
QFrame#StatCard[accent="green"]  {{ border-top: 2px solid {ACCENT_GREEN}; }}
QFrame#StatCard[accent="amber"]  {{ border-top: 2px solid {ACCENT_AMBER}; }}
QFrame#StatCard[accent="red"]    {{ border-top: 2px solid {ACCENT_RED}; }}

QLabel#StatCardTitle {{
    color: {TEXT_MUTED};
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 0.12em;
}}

QLabel#StatCardValue {{
    color: #ffffff;
    font-size: 24px;
    font-weight: 800;
    letter-spacing: -0.6px;
}}

QLabel#StatCardSub {{
    color: {TEXT_DIM};
    font-size: 11px;
    font-weight: 500;
}}

QLabel#StatCardTrend {{
    font-size: 11px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 999px;
}}
QLabel#StatCardTrend[trend="up"] {{
    color: #86efac; background: rgba(34, 197, 94, 0.16);
    border: 1px solid rgba(34, 197, 94, 0.35);
}}
QLabel#StatCardTrend[trend="down"] {{
    color: #fca5a5; background: rgba(239, 68, 68, 0.16);
    border: 1px solid rgba(239, 68, 68, 0.35);
}}
QLabel#StatCardTrend[trend="flat"] {{
    color: #cbd5e1; background: rgba(148, 163, 184, 0.14);
    border: 1px solid rgba(148, 163, 184, 0.3);
}}

/* ==========================================================================
   INPUTS
   ========================================================================== */
QLineEdit, QComboBox, QSpinBox {{
    background: rgba(14, 20, 32, 0.85);
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: 9px;
    padding: 8px 12px;
    color: #f8fafc;
    font-size: 13px;
    selection-background-color: {ACCENT_PRIMARY};
    selection-color: #ffffff;
}}

QLineEdit:hover, QComboBox:hover, QSpinBox:hover {{
    border-color: rgba(147, 197, 253, 0.35);
    background: rgba(18, 25, 40, 0.9);
}}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
    border: 1px solid {ACCENT_PRIMARY};
    background: rgba(20, 28, 46, 0.95);
}}

QLineEdit[search="true"] {{
    padding-left: 32px;
    background-image: none;
}}

QComboBox::drop-down {{
    border: none;
    width: 26px;
}}

QComboBox QAbstractItemView {{
    background: rgba(18, 26, 42, 0.98);
    border: 1px solid {BORDER_STRONG};
    border-radius: 8px;
    padding: 4px;
    selection-background-color: rgba(59, 130, 246, 0.4);
    color: #ffffff;
    outline: none;
}}

/* ==========================================================================
   BUTTONS
   ========================================================================== */
QPushButton {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #3b82f6, stop:1 #2563eb);
    color: #ffffff;
    border: 1px solid rgba(255, 255, 255, 0.18);
    border-radius: 9px;
    padding: 8px 16px;
    font-weight: 600;
    font-size: 13px;
    min-height: 20px;
}}

QPushButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #60a5fa, stop:1 #3b82f6);
    border-color: rgba(255, 255, 255, 0.35);
}}

QPushButton:pressed {{
    background: #1d4ed8;
}}

QPushButton:focus {{
    border: 1px solid #93c5fd;
}}

QPushButton:disabled {{
    background: rgba(30, 41, 59, 0.5);
    color: #64748b;
    border: 1px solid rgba(255, 255, 255, 0.04);
}}

/* Icon-only button (ghost) */
QPushButton#IconButton {{
    background: rgba(255, 255, 255, 0.045);
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_SUBTLE};
    border-radius: 9px;
    padding: 6px;
    min-width: 32px;
    max-width: 32px;
    min-height: 32px;
    max-height: 32px;
}}
QPushButton#IconButton:hover {{
    background: rgba(255, 255, 255, 0.09);
    border-color: rgba(110, 168, 254, 0.4);
}}
QPushButton#IconButton:checked {{
    background: rgba(59, 130, 246, 0.22);
    border-color: rgba(96, 165, 250, 0.55);
}}

/* Secondary */
QPushButton#SecondaryButton, QPushButton#BrowseButton {{
    background: rgba(30, 41, 59, 0.7);
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_SUBTLE};
}}
QPushButton#SecondaryButton:hover, QPushButton#BrowseButton:hover {{
    background: rgba(51, 65, 85, 0.85);
    border-color: rgba(255, 255, 255, 0.22);
    color: #ffffff;
}}

/* Danger / Cancel */
QPushButton#CancelButton {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #ef4444, stop:1 #dc2626);
    border: 1px solid rgba(255, 255, 255, 0.15);
}}
QPushButton#CancelButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #f87171, stop:1 #ef4444);
}}

/* Primary run button */
QPushButton#RunButton {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #2563eb, stop:1 #7c3aed);
    border: 1px solid rgba(255, 255, 255, 0.25);
    font-weight: 700;
    padding: 8px 18px;
}}
QPushButton#RunButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #3b82f6, stop:1 #8b5cf6);
}}

/* Link button */
QPushButton#LinkButton {{
    background: transparent;
    border: none;
    color: #93c5fd;
    font-weight: 600;
    padding: 4px 8px;
    text-decoration: underline;
}}
QPushButton#LinkButton:hover {{
    color: #ffffff;
}}

/* ==========================================================================
   TABLES AND TREES
   ========================================================================== */
QTableWidget, QTreeWidget {{
    background: rgba(13, 19, 31, 0.68);
    border: 1px solid {BORDER_SUBTLE};
    border-radius: 12px;
    gridline-color: transparent;
    alternate-background-color: rgba(22, 30, 48, 0.36);
    selection-background-color: rgba(59, 130, 246, 0.28);
    selection-color: #ffffff;
    outline: none;
}}

QHeaderView {{
    background: transparent;
}}

QHeaderView::section {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(22, 30, 48, 0.98),
        stop:1 rgba(16, 22, 36, 0.98));
    color: {TEXT_MUTED};
    border: none;
    border-bottom: 1px solid {BORDER_SUBTLE};
    border-right: 1px solid {BORDER_SUBTLE};
    padding: 10px 14px;
    font-size: 10px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.10em;
}}

QHeaderView::section:last {{
    border-right: none;
}}

QHeaderView::section:hover {{
    background: rgba(30, 40, 62, 0.98);
    color: #ffffff;
}}

QTableWidget::item, QTreeWidget::item {{
    padding: 8px 12px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.025);
}}

QTableWidget::item:hover, QTreeWidget::item:hover {{
    background: rgba(255, 255, 255, 0.035);
}}

QTableWidget::item:selected, QTreeWidget::item:selected {{
    background: rgba(59, 130, 246, 0.28);
    color: #ffffff;
}}

QTreeWidget::branch {{
    background: transparent;
}}

/* ==========================================================================
   CHECKBOXES
   ========================================================================== */
QCheckBox {{
    color: {TEXT_PRIMARY};
    spacing: 10px;
    font-size: 13px;
    padding: 4px 0;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 1px solid rgba(255, 255, 255, 0.20);
    background: rgba(15, 21, 34, 0.9);
}}

QCheckBox::indicator:hover {{
    border-color: #60a5fa;
    background: rgba(24, 34, 54, 0.95);
}}

QCheckBox::indicator:checked {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #3b82f6, stop:1 #2563eb);
    border-color: #93c5fd;
}}

/* ==========================================================================
   PROGRESS BAR
   ========================================================================== */
QProgressBar {{
    border: none;
    background: rgba(255, 255, 255, 0.06);
    border-radius: 4px;
    text-align: center;
    color: transparent;
}}

QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {ACCENT_CYAN},
        stop:0.5 {ACCENT_PRIMARY},
        stop:1 {ACCENT_VIOLET});
    border-radius: 4px;
}}

/* ==========================================================================
   TABS
   ========================================================================== */
QTabWidget::pane {{
    border: 1px solid {BORDER_GLASS};
    border-radius: {RADIUS_MD}px;
    background: rgba(15, 21, 34, 0.55);
    top: -1px;
    padding: 4px;
}}

QTabBar::tab {{
    background: transparent;
    color: {TEXT_MUTED};
    border: 1px solid transparent;
    border-bottom: none;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
    padding: 8px 16px;
    margin-right: 4px;
    font-weight: 600;
    font-size: 12px;
    min-width: 80px;
}}

QTabBar::tab:hover:!selected {{
    background: rgba(255, 255, 255, 0.035);
    color: #cbd5e1;
}}

QTabBar::tab:selected {{
    background: rgba(23, 31, 48, 0.9);
    color: #ffffff;
    border-color: rgba(96, 165, 250, 0.4);
    border-bottom: 2px solid {ACCENT_PRIMARY};
}}

/* ==========================================================================
   SCROLLBARS
   ========================================================================== */
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: rgba(255, 255, 255, 0.14);
    min-height: 30px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical:hover {{
    background: rgba(255, 255, 255, 0.26);
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
    height: 0;
}}

QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 2px;
}}
QScrollBar::handle:horizontal {{
    background: rgba(255, 255, 255, 0.14);
    min-width: 30px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal:hover {{
    background: rgba(255, 255, 255, 0.26);
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: none;
    width: 0;
}}

/* ==========================================================================
   STATUS BAR + TOAST
   ========================================================================== */
#StatusBar {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(11, 16, 26, 0.9),
        stop:1 rgba(8, 12, 20, 0.95));
    border-top: 1px solid {BORDER_SUBTLE};
    padding: 6px 18px;
}}

#StatusBar QLabel {{
    color: {TEXT_MUTED};
    font-size: 12px;
    background: transparent;
}}

#StatusMessage {{
    color: #cbd5e1;
    font-weight: 600;
}}

#StatusMeta {{
    color: {TEXT_FAINT};
    font-weight: 500;
}}

#StatusDot[state="idle"]    {{ color: #64748b; }}
#StatusDot[state="running"] {{ color: {ACCENT_CYAN}; }}
#StatusDot[state="ok"]      {{ color: {ACCENT_GREEN}; }}
#StatusDot[state="warn"]    {{ color: {ACCENT_AMBER}; }}
#StatusDot[state="error"]   {{ color: {ACCENT_RED}; }}

#Toast {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(20, 28, 46, 0.98),
        stop:1 rgba(14, 20, 34, 0.98));
    border: 1px solid {BORDER_STRONG};
    border-radius: 12px;
    padding: 12px 18px;
    color: #ffffff;
    font-size: 13px;
    font-weight: 600;
}}

#Toast[toastKind="success"] {{ border-color: rgba(34, 197, 94, 0.55); }}
#Toast[toastKind="warning"] {{ border-color: rgba(245, 158, 11, 0.55); }}
#Toast[toastKind="error"]   {{ border-color: rgba(239, 68, 68, 0.55); }}

/* ==========================================================================
   MISC
   ========================================================================== */
#Divider {{
    background: {BORDER_SUBTLE};
    max-height: 1px;
    min-height: 1px;
}}

#TreeBox {{
    font-family: {MONO_FAMILY};
    font-size: 12px;
    color: #93c5fd;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(10, 15, 26, 0.92),
        stop:1 rgba(8, 12, 22, 0.92));
    border: 1px solid {BORDER_SUBTLE};
    border-radius: 10px;
    padding: 14px;
}}

#InsightCard {{
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid {BORDER_SUBTLE};
    border-left: 3px solid {ACCENT_PRIMARY};
    border-radius: 10px;
    padding: 10px 14px;
}}
#InsightCard[severity="critical"] {{ border-left-color: {ACCENT_RED}; }}
#InsightCard[severity="warning"]  {{ border-left-color: {ACCENT_AMBER}; }}
#InsightCard[severity="info"]     {{ border-left-color: {ACCENT_PRIMARY}; }}
#InsightCard[severity="success"]  {{ border-left-color: {ACCENT_GREEN}; }}

#EmptyStateIcon {{
    color: {TEXT_FAINT};
}}
#EmptyStateTitle {{
    color: #cbd5e1;
    font-size: 14px;
    font-weight: 700;
}}
#EmptyStateBody {{
    color: {TEXT_DIM};
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
        QPalette.ColorRole.Link: "#60a5fa",
    }
    for role, color in dark.items():
        palette.setColor(role, QColor(color))
    palette.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.BrightText,
                     QColor("#ffffff"))
    app.setPalette(palette)
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(STYLE_SHEET)