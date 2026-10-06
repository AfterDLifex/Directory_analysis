"""
Design-system theming for Folder Analysis Pro.

Refactored from one hard-coded stylesheet into a token-driven system:

* :class:`ThemeTokens` - every colour role, radius and font scale is a named
  token instead of an inline hex literal.
* :data:`THEMES` - six first-class themes (four dark, two light).
* :func:`build_stylesheet` - renders the full QSS from a token set, so a theme
  switch is a single ``QApplication.setStyleSheet`` call.
* :class:`ThemeManager` - singleton owning the live theme; persists theme,
  accent and density in ``QSettings`` and emits ``themeChanged`` so views can
  re-render anything QSS cannot express (charts, SVG icons).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Dict, List, Optional

from PySide6.QtCore import QObject, QSettings, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPalette

# ---------------------------------------------------------------------------
# Typography & spacing
# ---------------------------------------------------------------------------

FONT_SANS = ("'Segoe UI Variable Display', 'Segoe UI', -apple-system, "
             "BlinkMacSystemFont, 'Inter', Roboto, Ubuntu, 'Helvetica Neue', "
             "sans-serif")
FONT_MONO = ("'JetBrains Mono', 'Cascadia Mono', 'SFMono-Regular', Consolas, "
             "'Liberation Mono', Menlo, monospace")

#: Logical spacing scale (px); density scales the md/lg steps.
SPACE: Dict[str, int] = {"xs": 4, "sm": 8, "md": 12, "lg": 18, "xl": 26}

#: Accent ramp - user-overridable independently of the theme.
ACCENTS: Dict[str, str] = {
    "Indigo": "#6366f1",
    "Blue": "#3b82f6",
    "Cyan": "#06b6d4",
    "Emerald": "#10b981",
    "Amber": "#f59e0b",
    "Rose": "#f43f5e",
    "Violet": "#8b5cf6",
    "Slate": "#64748b",
}

DEFAULT_THEME = "midnight"
DENSITIES = ("Compact", "Comfortable", "Spacious")


# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------

def _hex_to_rgba(color: str, alpha: float) -> str:
    """``#3b82f6`` -> ``rgba(59,130,246,0.200)``.

    Tokens may already be ``rgba(...)``/``rgb(...)`` strings; those are parsed
    and re-emitted with the new alpha instead of being treated as hex.
    """
    c = color.strip()
    if c.startswith(("rgba", "rgb")):
        parts = c[c.index("(") + 1:c.index(")")].split(",")
        r, g, b = (int(float(parts[i])) for i in (0, 1, 2))
        return f"rgba({r},{g},{b},{alpha:.3f})"
    h = c.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha:.3f})"


def _flatten(color: str) -> str:
    """Resolve an ``rgba(...)`` token against a dark base to an opaque hex."""
    if not color.startswith("rgba"):
        return color
    parts = color[color.index("(") + 1:color.index(")")].split(",")
    r, g, b = int(float(parts[0])), int(float(parts[1])), int(float(parts[2]))
    a = float(parts[3]) if len(parts) > 3 else 1.0
    base = (13, 17, 27)
    return "#{:02x}{:02x}{:02x}".format(
        int(r * a + base[0] * (1 - a)),
        int(g * a + base[1] * (1 - a)),
        int(b * a + base[2] * (1 - a)),
    )


def _blend(a: str, b: str) -> str:
    """50/50 blend of two hex colours."""
    ah, bh = a.lstrip("#"), b.lstrip("#")
    return "#{:02x}{:02x}{:02x}".format(*[
        (int(ah[i:i + 2], 16) + int(bh[i:i + 2], 16)) // 2 for i in (0, 2, 4)
    ])


# ---------------------------------------------------------------------------
# Token model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ThemeTokens:
    """A complete visual language - one row of the theme table."""

    key: str
    name: str
    dark: bool = True

    # root background gradient stops
    bg_1: str = "#070b13"
    bg_2: str = "#0a1120"
    bg_3: str = "#070c16"

    # surfaces
    chrome: str = "rgba(13, 19, 32, 0.94)"       # top bar / nav / status bar
    surface: str = "rgba(22, 30, 48, 0.72)"       # panel fill
    surface_alt: str = "rgba(14, 20, 34, 0.68)"   # recessed fill
    surface_input: str = "rgba(10, 15, 26, 0.9)"  # inputs, code, tree view
    hover: str = "rgba(255, 255, 255, 0.055)"
    pressed: str = "rgba(255, 255, 255, 0.09)"

    # lines
    border: str = "rgba(255, 255, 255, 0.07)"
    border_strong: str = "rgba(255, 255, 255, 0.13)"
    border_focus: str = "rgba(120, 170, 255, 0.65)"

    # text
    text: str = "#e8eefb"
    text_strong: str = "#ffffff"
    text_dim: str = "#93a7c6"
    text_muted: str = "#64748b"
    text_faint: str = "#4c5f7d"

    # brand + semantics
    accent: str = "#4f8cff"
    accent_2: str = "#8b5cf6"
    accent_text: str = "#ffffff"
    success: str = "#22c55e"
    warning: str = "#f59e0b"
    danger: str = "#ef4444"
    info: str = "#38bdf8"

    # chart series (shared with the QtCharts helpers in pages.py)
    series: tuple = ()

    # geometry
    radius_sm: int = 8
    radius_md: int = 12
    radius_lg: int = 16
    radius_pill: int = 999

    # typography scale
    fs_display: int = 26
    fs_title: int = 15
    fs_body: int = 13
    fs_small: int = 11
    fs_micro: int = 10

    def with_accent(self, hex_color: str) -> "ThemeTokens":
        """Return a copy of this theme tinted with ``hex_color``."""
        return replace(self, accent=hex_color)

    def as_palette(self) -> QPalette:
        """Native palette so popups and dialogs inherit the theme colours."""
        p = QPalette()
        p.setColor(QPalette.ColorRole.Window, QColor(_blend(self.bg_1, self.bg_2)))
        p.setColor(QPalette.ColorRole.WindowText, QColor(self.text))
        p.setColor(QPalette.ColorRole.Base, QColor(_flatten(self.surface_input)))
        p.setColor(QPalette.ColorRole.AlternateBase,
                   QColor(_blend(_flatten(self.surface), self.bg_2)))
        p.setColor(QPalette.ColorRole.ToolTipBase,
                   QColor(_blend(_flatten(self.chrome), self.bg_2)))
        p.setColor(QPalette.ColorRole.ToolTipText, QColor(self.text_strong))
        p.setColor(QPalette.ColorRole.Text, QColor(self.text))
        p.setColor(QPalette.ColorRole.Button, QColor(_flatten(self.chrome)))
        p.setColor(QPalette.ColorRole.ButtonText, QColor(self.text_strong))
        p.setColor(QPalette.ColorRole.Highlight, QColor(self.accent))
        p.setColor(QPalette.ColorRole.HighlightedText, QColor(self.accent_text))
        p.setColor(QPalette.ColorRole.PlaceholderText, QColor(self.text_muted))
        p.setColor(QPalette.ColorRole.Link, QColor(self.accent))
        disabled = (QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText,
                    QPalette.ColorRole.WindowText)
        for role in disabled:
            p.setColor(QPalette.ColorGroup.Disabled, role, QColor(self.text_faint))
        return p


_DARK_SERIES = ("#4f8cff", "#8b5cf6", "#06b6d4", "#22c55e", "#f59e0b",
                "#f43f5e", "#a855f7", "#14b8a6", "#eab308", "#64748b")
_LIGHT_SERIES = ("#2563eb", "#7c3aed", "#0891b2", "#059669", "#d97706",
                 "#e11d48", "#9333ea", "#0d9488", "#ca8a04", "#475569")
# ---------------------------------------------------------------------------
# Theme table - adding a theme means adding one row here.
# ---------------------------------------------------------------------------

THEMES: Dict[str, ThemeTokens] = {
    "midnight": ThemeTokens(
        key="midnight", name="Midnight", dark=True,
        bg_1="#05080f", bg_2="#0a1120", bg_3="#060a13",
        accent="#4f8cff", accent_2="#8b5cf6", series=_DARK_SERIES,
    ),
    "obsidian": ThemeTokens(
        key="obsidian", name="Obsidian", dark=True,
        bg_1="#0b0c0f", bg_2="#131519", bg_3="#0a0b0e",
        chrome="rgba(19, 20, 24, 0.94)",
        surface="rgba(30, 32, 38, 0.68)", surface_alt="rgba(20, 21, 25, 0.7)",
        surface_input="rgba(14, 15, 18, 0.92)",
        border="rgba(255, 255, 255, 0.08)",
        border_strong="rgba(255, 255, 255, 0.16)",
        text="#e9eaee", text_dim="#9ba0ab", text_muted="#6b7079",
        text_faint="#4b5058",
        accent="#38bdf8", accent_2="#818cf8", series=_DARK_SERIES,
    ),
    "aurora": ThemeTokens(
        key="aurora", name="Aurora", dark=True,
        bg_1="#08110f", bg_2="#0c1c1b", bg_3="#060e0d",
        surface="rgba(16, 40, 38, 0.7)", surface_alt="rgba(10, 27, 26, 0.7)",
        surface_input="rgba(6, 20, 19, 0.9)",
        text="#e2f5f0", text_dim="#8fc3ba", text_muted="#5d8a83",
        text_faint="#3f6560",
        accent="#2dd4bf", accent_2="#4ade80", series=_DARK_SERIES,
    ),
    "noir": ThemeTokens(
        key="noir", name="Noir", dark=True,
        bg_1="#000000", bg_2="#0a0a0c", bg_3="#050506",
        chrome="rgba(10, 10, 12, 0.95)",
        surface="rgba(24, 24, 27, 0.7)", surface_alt="rgba(14, 14, 16, 0.72)",
        surface_input="rgba(8, 8, 10, 0.92)",
        border="rgba(255, 255, 255, 0.09)",
        border_strong="rgba(255, 255, 255, 0.18)",
        text="#f4f4f5", text_dim="#a1a1aa", text_muted="#71717a",
        text_faint="#52525b",
        accent="#e4e4e7", accent_2="#a1a1aa", accent_text="#09090b",
        success="#4ade80", info="#93c5fd", series=_DARK_SERIES,
    ),
    "daylight": ThemeTokens(
        key="daylight", name="Daylight", dark=False,
        bg_1="#e9eff8", bg_2="#f8fafd", bg_3="#e2e9f4",
        chrome="rgba(255, 255, 255, 0.9)",
        surface="rgba(255, 255, 255, 0.92)",
        surface_alt="rgba(243, 247, 252, 0.95)",
        surface_input="rgba(255, 255, 255, 0.98)",
        hover="rgba(15, 23, 42, 0.045)", pressed="rgba(15, 23, 42, 0.08)",
        border="rgba(15, 23, 42, 0.10)",
        border_strong="rgba(15, 23, 42, 0.18)",
        border_focus="rgba(37, 99, 235, 0.75)",
        text="#0f172a", text_strong="#020617", text_dim="#475569",
        text_muted="#64748b", text_faint="#94a3b8",
        accent="#2563eb", accent_2="#7c3aed",
        success="#059669", warning="#b45309", danger="#dc2626", info="#0284c7",
        series=_LIGHT_SERIES,
    ),
    "parchment": ThemeTokens(
        key="parchment", name="Parchment", dark=False,
        bg_1="#f4eee3", bg_2="#fcf9f2", bg_3="#ebe3d3",
        chrome="rgba(255, 252, 245, 0.92)",
        surface="rgba(255, 253, 248, 0.94)",
        surface_alt="rgba(245, 239, 228, 0.95)",
        surface_input="rgba(255, 255, 255, 0.98)",
        hover="rgba(80, 60, 30, 0.05)", pressed="rgba(80, 60, 30, 0.09)",
        border="rgba(87, 67, 41, 0.14)",
        border_strong="rgba(87, 67, 41, 0.24)",
        text="#2f2718", text_strong="#1a1509", text_dim="#5d5140",
        text_muted="#8a7c66", text_faint="#ab9c85",
        accent="#b45309", accent_2="#0f766e",
        success="#15803d", warning="#b45309", danger="#b91c1c", info="#0e7490",
        series=_LIGHT_SERIES,
    ),
}
# ---------------------------------------------------------------------------
# Stylesheet sections. Each helper returns one self-contained block so the
# sheet stays readable and diff-friendly.
# ---------------------------------------------------------------------------

def _qss_base(t: ThemeTokens) -> str:
    return f"""
QWidget {{
    color: {t.text};
    font-family: {FONT_SANS};
    font-size: {t.fs_body}px;
    outline: none;
}}
QMainWindow, QWidget#RootContainer {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {t.bg_1}, stop:0.45 {t.bg_2}, stop:1.0 {t.bg_3});
}}
QWidget#PageRoot, QStackedWidget > QWidget,
QScrollArea, QScrollArea > QWidget > QWidget {{ background: transparent; }}
QToolTip {{
    background: {_flatten(t.chrome)};
    color: {t.text_strong};
    border: 1px solid {t.border_strong};
    border-radius: {t.radius_sm}px;
    padding: 6px 11px;
    font-size: {t.fs_small}px;
}}
QLabel {{ background: transparent; }}
"""


def _qss_chrome(t: ThemeTokens) -> str:
    flat = _flatten(t.chrome)
    return f"""
#TopBar {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {flat}, stop:1 {_blend(flat, t.bg_3)});
    border-bottom: 1px solid {t.border};
}}
#AppLogoBadge {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {t.accent}, stop:1 {t.accent_2});
    color: {t.accent_text};
    font-weight: 800; font-size: {t.fs_micro}px;
    padding: 5px 10px; border-radius: {t.radius_sm}px;
    border: 1px solid {t.border_strong};
    letter-spacing: 0.14em;
}}
#TopBarTitle {{ color: {t.text_strong}; font-size: {t.fs_title}px; font-weight: 700; }}
#TopBarSubtitle {{ color: {t.text_dim}; font-size: {t.fs_small}px; }}
#TopBarSeparator {{ background: {t.border}; max-width: 1px; min-width: 1px; }}
#TopBarPath {{
    background: {t.surface_input};
    border: 1px solid {t.border};
    border-radius: {t.radius_sm}px;
    padding: 7px 12px;
    font-family: {FONT_MONO}; font-size: {t.fs_small}px;
    color: {t.text_dim};
}}
#StatusBar {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {flat}, stop:1 {_blend(flat, t.bg_3)});
    border-top: 1px solid {t.border};
}}
#StatusBar QLabel {{ color: {t.text_dim}; font-size: {t.fs_small}px; }}
#StatusMessage {{ color: {t.text}; font-weight: 600; }}
#StatusMeta {{ color: {t.text_faint}; font-weight: 500; }}
#StatusDot[state="idle"]    {{ color: {t.text_muted}; }}
#StatusDot[state="running"] {{ color: {t.info}; }}
#StatusDot[state="ok"]      {{ color: {t.success}; }}
#StatusDot[state="warn"]    {{ color: {t.warning}; }}
#StatusDot[state="error"]   {{ color: {t.danger}; }}
"""


def _qss_nav(t: ThemeTokens) -> str:
    return f"""
#NavContainer {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {_flatten(t.chrome)},
        stop:1 {_blend(_flatten(t.chrome), t.bg_2)});
    border-right: 1px solid {t.border};
}}
#NavSectionLabel {{
    color: {t.text_faint}; font-size: {t.fs_micro}px; font-weight: 800;
    letter-spacing: 0.16em; padding: 14px 16px 6px 16px;
}}
#NavList {{ background: transparent; border: none; outline: none; }}
#NavList::item {{
    height: 38px; margin: 2px 6px; padding: 0 10px;
    border-radius: {t.radius_sm + 2}px;
    color: {t.text_dim};
    background: transparent;
    border: 1px solid transparent;
    font-weight: 600;
    outline: 0;
}}
#NavList::item:hover {{
    background: {t.hover}; color: {t.text_strong};
    border: 1px solid {t.border};
}}
#NavList::item:selected, #NavList::item:selected:focus, #NavList::item:selected:active {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {_hex_to_rgba(t.accent, 0.30)},
        stop:1 {_hex_to_rgba(t.accent_2, 0.16)});
    color: {t.text_strong};
    border: 1px solid {_hex_to_rgba(t.accent, 0.55)};
    font-weight: 700;
    outline: 0;
}}
#NavHint {{
    color: {t.text_faint}; font-size: {t.fs_micro}px;
    padding: 4px 16px 10px 16px;
}}
#SidebarStat {{
    background: {t.surface_alt};
    border: 1px solid {t.border};
    border-radius: {t.radius_md}px;
    margin: 2px 10px;
}}
#SidebarStatLabel {{
    color: {t.text_faint}; font-size: {t.fs_micro}px;
    font-weight: 700; letter-spacing: 0.1em;
}}
#SidebarStatValue {{
    color: {t.text_strong}; font-size: 15px; font-weight: 700;
}}
"""


def _qss_surfaces(t: ThemeTokens) -> str:
    return f"""
QFrame#GlassPanel {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {_hex_to_rgba(t.surface, 0.92)},
        stop:1 {_hex_to_rgba(t.surface_alt, 0.88)});
    border: 1px solid {t.border};
    border-radius: {t.radius_lg}px;
}}
QFrame#GlassPanel:hover {{ border-color: {_hex_to_rgba(t.accent, 0.28)}; }}
QFrame#StatCard {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {_hex_to_rgba(t.surface, 0.95)},
        stop:1 {_hex_to_rgba(t.surface_alt, 0.90)});
    border: 1px solid {t.border};
    border-radius: {t.radius_md + 2}px;
    min-height: 92px;
}}
QFrame#StatCard:hover {{
    border-color: {_hex_to_rgba(t.accent, 0.42)};
}}
QFrame#StatCard[accent="cyan"]   {{ border-top: 2px solid {t.info}; }}
QFrame#StatCard[accent="blue"]   {{ border-top: 2px solid {t.accent}; }}
QFrame#StatCard[accent="violet"] {{ border-top: 2px solid {t.accent_2}; }}
QFrame#StatCard[accent="green"]  {{ border-top: 2px solid {t.success}; }}
QFrame#StatCard[accent="amber"]  {{ border-top: 2px solid {t.warning}; }}
QFrame#StatCard[accent="red"]    {{ border-top: 2px solid {t.danger}; }}
QLabel#PanelTitle {{
    color: {t.text_strong}; font-size: {t.fs_body}px; font-weight: 700;
}}
QLabel#PanelSubtitle, QLabel#SectionSubtitle {{
    color: {t.text_faint}; font-size: {t.fs_small}px;
}}
QLabel#SectionTitle {{
    color: {t.text_strong}; font-size: {t.fs_body}px;
    font-weight: 800; letter-spacing: 0.02em;
}}
QLabel#StatCardTitle {{
    color: {t.text_dim}; font-size: {t.fs_micro}px;
    font-weight: 800; letter-spacing: 0.12em;
}}
QLabel#StatCardValue {{
    color: {t.text_strong}; font-size: {t.fs_display}px;
    font-weight: 800; letter-spacing: -0.6px;
}}
QLabel#StatCardSub {{ color: {t.text_muted}; font-size: {t.fs_small}px; }}
QLabel#StatCardTrend {{
    font-size: {t.fs_micro}px; font-weight: 700;
    padding: 2px 8px; border-radius: {t.radius_pill}px;
}}
QLabel#StatCardTrend[trend="up"] {{
    color: {t.success}; background: {_hex_to_rgba(t.success, 0.14)};
    border: 1px solid {_hex_to_rgba(t.success, 0.35)};
}}
QLabel#StatCardTrend[trend="down"] {{
    color: {t.danger}; background: {_hex_to_rgba(t.danger, 0.14)};
    border: 1px solid {_hex_to_rgba(t.danger, 0.35)};
}}
QLabel#StatCardTrend[trend="flat"] {{
    color: {t.text_dim}; background: {_hex_to_rgba(t.text_muted, 0.14)};
    border: 1px solid {_hex_to_rgba(t.text_muted, 0.30)};
}}
#PanelBadge {{
    color: {t.text_dim}; background: {t.hover};
    border: 1px solid {t.border};
    border-radius: {t.radius_pill}px;
    padding: 2px 10px;
    font-size: {t.fs_small}px; font-weight: 700;
}}
#InsightCard {{
    background: {t.surface_alt};
    border: 1px solid {t.border};
    border-left: 3px solid {t.accent};
    border-radius: {t.radius_md}px;
}}
#InsightCard[severity="critical"] {{ border-left-color: {t.danger}; }}
#InsightCard[severity="warning"]  {{ border-left-color: {t.warning}; }}
#InsightCard[severity="info"]     {{ border-left-color: {t.accent}; }}
#InsightCard[severity="success"]  {{ border-left-color: {t.success}; }}
#TreeBox, QPlainTextEdit#CodeView {{
    font-family: {FONT_MONO}; font-size: {t.fs_small}px;
    color: {t.text_dim};
    background: {t.surface_input};
    border: 1px solid {t.border};
    border-radius: {t.radius_md}px;
    padding: 12px;
    selection-background-color: {t.accent};
    selection-color: {t.accent_text};
}}
#EmptyStateTitle {{
    color: {t.text_dim}; font-size: {t.fs_title}px; font-weight: 700;
}}
#EmptyStateBody {{ color: {t.text_muted}; font-size: {t.fs_small}px; }}
"""
def _qss_controls(t: ThemeTokens) -> str:
    return f"""
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPlainTextEdit, QTextEdit {{
    background: {t.surface_input};
    border: 1px solid {t.border_strong};
    border-radius: {t.radius_sm}px;
    padding: 8px 12px;
    color: {t.text_strong};
    font-size: {t.fs_body}px;
    selection-background-color: {t.accent};
    selection-color: {t.accent_text};
    placeholder-text-color: {t.text_muted};
}}
QLineEdit:hover, QComboBox:hover, QSpinBox:hover {{
    border-color: {_hex_to_rgba(t.accent, 0.40)};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QPlainTextEdit:focus {{
    border: 1px solid {t.accent};
}}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled {{
    color: {t.text_faint};
}}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox::down-arrow {{ image: none; }}
QComboBox QAbstractItemView {{
    background: {_flatten(t.chrome)};
    border: 1px solid {t.border_strong};
    border-radius: {t.radius_sm}px;
    padding: 4px;
    selection-background-color: {_hex_to_rgba(t.accent, 0.35)};
    outline: none;
}}
QSpinBox::up-button, QSpinBox::down-button {{
    width: 16px; background: transparent;
}}
QPushButton {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {_blend(_flatten(t.chrome), t.bg_2)},
        stop:1 {_flatten(t.chrome)});
    color: {t.text};
    border: 1px solid {t.border_strong};
    border-radius: {t.radius_sm}px;
    padding: 8px 16px;
    font-weight: 600;
    font-size: {t.fs_body}px;
    min-height: 20px;
}}
QPushButton:hover {{ background: {t.hover}; color: {t.text_strong}; }}
QPushButton:pressed {{ background: {t.pressed}; }}
QPushButton:disabled {{
    color: {t.text_faint};
    border: 1px solid {t.border};
    background: {t.surface_alt};
}}
QPushButton#IconButton {{
    background: {t.hover};
    border: 1px solid {t.border};
    border-radius: {t.radius_sm}px;
    padding: 6px;
    min-width: 32px; max-width: 32px;
    min-height: 32px; max-height: 32px;
}}
QPushButton#IconButton:hover {{
    background: {t.pressed};
    border-color: {_hex_to_rgba(t.accent, 0.50)};
    color: {t.text_strong};
}}
QPushButton#IconButton:checked {{
    background: {_hex_to_rgba(t.accent, 0.22)};
    border-color: {_hex_to_rgba(t.accent, 0.65)};
}}
QPushButton#RunButton {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {t.accent}, stop:1 {t.accent_2});
    border: 1px solid {_hex_to_rgba(t.accent, 0.60)};
    color: {t.accent_text};
    font-weight: 700;
    padding: 8px 18px;
}}
QPushButton#RunButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {_blend(t.accent, "#ffffff")},
        stop:1 {_blend(t.accent_2, "#ffffff")});
}}
QPushButton#RunButton:disabled {{
    background: {t.surface_alt};
    color: {t.text_faint};
    border: 1px solid {t.border};
}}
QPushButton#DangerButton {{
    background: {_hex_to_rgba(t.danger, 0.16)};
    color: {t.danger};
    border: 1px solid {_hex_to_rgba(t.danger, 0.50)};
    font-weight: 700;
}}
QPushButton#DangerButton:hover {{ background: {_hex_to_rgba(t.danger, 0.28)}; }}
QPushButton#GhostButton {{
    background: transparent;
    border: 1px solid {t.border};
    color: {t.text_dim};
}}
QPushButton#GhostButton:hover {{
    background: {t.hover}; color: {t.text_strong};
    border-color: {t.border_strong};
}}
QPushButton#SegmentButton {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: {t.radius_sm}px;
    color: {t.text_dim};
    padding: 6px 14px;
    font-weight: 600;
}}
QPushButton#SegmentButton:hover {{
    background: {t.hover}; color: {t.text_strong};
}}
QPushButton#SegmentButton:checked {{
    background: {_hex_to_rgba(t.accent, 0.24)};
    border: 1px solid {_hex_to_rgba(t.accent, 0.55)};
    color: {t.text_strong};
}}
QCheckBox, QRadioButton {{ color: {t.text}; spacing: 10px; padding: 3px 0; }}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 18px; height: 18px;
    border: 1px solid {t.border_strong};
    background: {t.surface_input};
}}
QCheckBox::indicator {{ border-radius: 5px; }}
QRadioButton::indicator {{ border-radius: 9px; }}
QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
    border-color: {_hex_to_rgba(t.accent, 0.60)};
}}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background: {t.accent};
    border-color: {_blend(t.accent, "#ffffff")};
}}
QSlider::groove:horizontal {{
    height: 5px; background: {t.surface_alt};
    border: 1px solid {t.border}; border-radius: 3px;
}}
QSlider::handle:horizontal {{
    background: {t.accent}; width: 16px; height: 16px;
    margin: -7px 0; border-radius: 8px;
}}
QSlider::sub-page:horizontal {{ background: {t.accent}; border-radius: 3px; }}
QProgressBar {{
    border: none; background: {t.surface_alt};
    border-radius: 4px; text-align: center; color: transparent;
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {t.info}, stop:0.5 {t.accent}, stop:1 {t.accent_2});
    border-radius: 4px;
}}
"""
def _qss_data(t: ThemeTokens) -> str:
    return f"""
QTableView, QTableWidget, QTreeView, QTreeWidget, QListView {{
    background: {t.surface_alt};
    border: 1px solid {t.border};
    border-radius: {t.radius_md}px;
    gridline-color: transparent;
    alternate-background-color: {_hex_to_rgba(t.surface, 0.35)};
    selection-background-color: {_hex_to_rgba(t.accent, 0.28)};
    selection-color: {t.text_strong};
    outline: none;
}}
QHeaderView {{ background: transparent; }}
QHeaderView::section {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {_hex_to_rgba(t.surface, 0.98)},
        stop:1 {_hex_to_rgba(t.surface_alt, 0.98)});
    color: {t.text_dim};
    border: none;
    border-bottom: 1px solid {t.border};
    border-right: 1px solid {t.border};
    padding: 9px 13px;
    font-size: {t.fs_micro}px; font-weight: 800;
    text-transform: uppercase; letter-spacing: 0.10em;
}}
QHeaderView::section:last {{ border-right: none; }}
QTableView::item, QTreeView::item {{
    padding: 7px 11px;
    border-bottom: 1px solid {_hex_to_rgba(t.border, 0.40)};
}}
QTableView::item:selected, QTreeView::item:selected {{
    background: {_hex_to_rgba(t.accent, 0.28)};
    color: {t.text_strong};
}}
QTableCornerButton::section {{ background: transparent; border: none; }}
QTabWidget::pane {{
    border: 1px solid {t.border};
    border-radius: {t.radius_md}px;
    background: {_hex_to_rgba(t.surface_alt, 0.55)};
    top: -1px; padding: 4px;
}}
QTabBar::tab {{
    background: transparent; color: {t.text_dim};
    border: 1px solid transparent; border-bottom: none;
    border-top-left-radius: {t.radius_md - 2}px;
    border-top-right-radius: {t.radius_md - 2}px;
    padding: 8px 16px; margin-right: 4px;
    font-weight: 600; font-size: {t.fs_small + 1}px;
    min-width: 76px;
}}
QTabBar::tab:selected {{
    background: {_hex_to_rgba(t.surface, 0.90)};
    color: {t.text_strong};
    border-color: {_hex_to_rgba(t.accent, 0.40)};
    border-bottom: 2px solid {t.accent};
}}
QTabBar::tab:hover:!selected {{ background: {t.hover}; color: {t.text}; }}
QTabBar::tab:disabled {{ color: {t.text_faint}; }}
QSplitter::handle {{ background: transparent; }}
QSplitter::handle:horizontal {{ width: 10px; }}
QSplitter::handle:vertical {{ height: 10px; }}
QSplitter::handle:hover {{ background: {_hex_to_rgba(t.accent, 0.20)}; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{
    background: {_hex_to_rgba(t.text_muted, 0.45)};
    min-height: 30px; border-radius: 4px;
}}
QScrollBar::handle:vertical:hover {{
    background: {_hex_to_rgba(t.text_dim, 0.70)};
}}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{
    background: {_hex_to_rgba(t.text_muted, 0.45)};
    min-width: 30px; border-radius: 4px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {_hex_to_rgba(t.text_dim, 0.70)};
}}
QScrollBar::add-line, QScrollBar::sub-line {{
    width: 0; height: 0; border: none;
}}
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}
"""
def _qss_feedback(t: ThemeTokens) -> str:
    flat = _flatten(t.chrome)
    return f"""
#Toast {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {flat}, stop:1 {_blend(flat, t.bg_3)});
    border: 1px solid {t.border_strong};
    border-left: 3px solid {t.accent};
    border-radius: {t.radius_md}px;
    color: {t.text_strong};
    font-size: {t.fs_body}px; font-weight: 600;
}}
#Toast[toastKind="success"] {{ border-left-color: {t.success}; }}
#Toast[toastKind="warning"] {{ border-left-color: {t.warning}; }}
#Toast[toastKind="error"]   {{ border-left-color: {t.danger}; }}
#Toast[toastKind="info"]    {{ border-left-color: {t.info}; }}
#ModalRoot {{ background: {_hex_to_rgba(t.bg_3, 0.72)}; }}
#ModalCard {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {_hex_to_rgba(t.surface, 0.99)},
        stop:1 {_hex_to_rgba(t.surface_alt, 0.99)});
    border: 1px solid {t.border_strong};
    border-radius: {t.radius_lg}px;
}}
#ModalTitle {{
    color: {t.text_strong}; font-size: {t.fs_title + 2}px; font-weight: 800;
}}
#ModalBody  {{ color: {t.text_dim}; font-size: {t.fs_body}px; }}
#ModalMeta  {{ color: {t.text_faint}; font-size: {t.fs_small}px; }}
#ModalIcon {{
    background: {_hex_to_rgba(t.accent, 0.14)};
    border: 1px solid {_hex_to_rgba(t.accent, 0.35)};
    border-radius: {t.radius_md}px;
}}
#ModalIcon[state="success"] {{
    background: {_hex_to_rgba(t.success, 0.16)};
    border-color: {_hex_to_rgba(t.success, 0.45)};
}}
#ModalIcon[state="error"] {{
    background: {_hex_to_rgba(t.danger, 0.16)};
    border-color: {_hex_to_rgba(t.danger, 0.45)};
}}
#StageRow {{
    background: {t.surface_alt};
    border: 1px solid {t.border};
    border-radius: {t.radius_md}px;
}}
#StageRow[state="running"] {{ border-color: {_hex_to_rgba(t.accent, 0.55)}; }}
#StageRow[state="done"]    {{ border-color: {_hex_to_rgba(t.success, 0.45)}; }}
#StageRow[state="failed"]  {{ border-color: {_hex_to_rgba(t.danger, 0.50)}; }}
#StageLabel  {{ color: {t.text}; font-size: {t.fs_body}px; font-weight: 600; }}
#StageDetail {{ color: {t.text_faint}; font-size: {t.fs_small}px; }}
QLabel#ShortcutKey {{
    color: {t.text_strong};
    background: {t.surface_alt};
    border: 1px solid {t.border_strong};
    border-bottom-width: 2px;
    border-radius: {t.radius_sm - 2}px;
    padding: 3px 9px;
    font-family: {FONT_MONO}; font-size: {t.fs_small}px; font-weight: 700;
}}
QLabel#ShortcutDesc {{
    color: {t.text_dim}; font-size: {t.fs_body}px;
}}
#Divider {{ background: {t.border}; max-height: 1px; min-height: 1px; }}
QScrollArea#PageScroll {{ background: transparent; border: none; }}
#Swatch {{
    border: 2px solid {t.border_strong};
    border-radius: {t.radius_sm}px;
}}
#Swatch[state="selected"] {{ border-color: {t.accent}; }}
"""
def build_stylesheet(t: ThemeTokens) -> str:
    """Render the complete application stylesheet for one token set."""
    return "".join((
        _qss_base(t), _qss_chrome(t), _qss_nav(t), _qss_surfaces(t),
        _qss_controls(t), _qss_data(t), _qss_feedback(t),
    ))


# ---------------------------------------------------------------------------
# Theme manager
# ---------------------------------------------------------------------------

class ThemeManager(QObject):
    """Owns the live :class:`ThemeTokens` and applies them to the app.

    Views subscribe to :attr:`themeChanged` to re-render non-QSS visuals
    (QtCharts themes, cached SVG icon colours).
    """

    themeChanged = Signal(object)   # ThemeTokens
    accentChanged = Signal(str)
    densityChanged = Signal(str)

    _instance: Optional["ThemeManager"] = None

    def __init__(self, app, parent: QObject | None = None) -> None:
        super().__init__(parent or app)
        self._app = app
        self._settings = QSettings("AfterDLifex", "FolderAnalysisPro")
        self._tokens: ThemeTokens = THEMES[DEFAULT_THEME]
        # --- theme-switch coalescing -------------------------------------
        # ``QApplication.setStyleSheet`` cannot be chunked - Qt reparses and
        # re-evaluates the sheet against the whole widget tree in one
        # blocking call. What we *can* do is:
        #   * coalesce a burst of clicks into a single apply, and
        #   * defer the apply to the next event-loop turn so the click
        #     handler returns first and the button's own hover/press state
        #     is painted before the freeze starts.
        self._apply_timer: Optional[QTimer] = None
        self._pending_tokens: Optional[ThemeTokens] = None
        self._flush_timer: Optional[QTimer] = None

    # -- construction ------------------------------------------------------

    @classmethod
    def instance(cls, app=None) -> "ThemeManager":
        if cls._instance is None:
            if app is None:
                from PySide6.QtWidgets import QApplication
                app = QApplication.instance()
            if app is None:
                raise RuntimeError("ThemeManager requires a QApplication")
            cls._instance = cls(app)
        return cls._instance

    @classmethod
    def current(cls) -> ThemeTokens:
        inst = cls._instance
        return inst.tokens if inst is not None else THEMES[DEFAULT_THEME]

    # -- accessors ---------------------------------------------------------

    @property
    def tokens(self) -> ThemeTokens:
        return self._tokens

    @property
    def is_dark(self) -> bool:
        return self._tokens.dark

    @property
    def accent(self) -> str:
        return self._tokens.accent

    @property
    def density(self) -> str:
        return str(self._settings.value("density", "Comfortable"))

    def available_themes(self) -> List[str]:
        return list(THEMES.keys())

    # -- mutators ----------------------------------------------------------

    def set_theme(self, key: str) -> None:
        if self._tokens is not None and self._tokens.key == key:
            return
        tokens = THEMES.get(key)
        if tokens is None:
            raise KeyError(f"Unknown theme: {key}")
        self._settings.setValue("theme", key)
        saved_accent = str(self._settings.value("accent", "") or "")
        self._tokens = tokens.with_accent(saved_accent or tokens.accent)
        self._schedule_apply()

    def toggle_theme(self) -> None:
        if self._tokens.dark:
            self.set_theme(next(k for k, v in THEMES.items() if not v.dark))
        else:
            self.set_theme(next(k for k, v in THEMES.items() if v.dark))

    def set_accent(self, hex_color: str) -> None:
        if not hex_color:
            return
        if self._tokens.accent.lower() == hex_color.lower():
            return
        self._settings.setValue("accent", hex_color)
        self._tokens = self._tokens.with_accent(hex_color)
        self.accentChanged.emit(hex_color)
        self._schedule_apply()

    def set_density(self, name: str) -> None:
        self._settings.setValue("density", name)
        self.densityChanged.emit(name)

    def reset_appearance(self) -> None:
        self._settings.remove("accent")
        self._settings.remove("density")
        self.set_theme(DEFAULT_THEME)

    # -- application -------------------------------------------------------

    def load_preferences(self) -> None:
        key = str(self._settings.value("theme", DEFAULT_THEME))
        tokens = THEMES.get(key, THEMES[DEFAULT_THEME])
        accent = str(self._settings.value("accent", "") or tokens.accent)
        self._tokens = tokens.with_accent(accent)
        # Apply synchronously at startup: the first stylesheet push is
        # dominated by initial layout, not by the switch itself.
        self._apply()
        self._schedule_fanout(immediate=True)

    def _schedule_apply(self) -> None:
        """Coalesce a burst of theme/accent clicks into one apply pass."""
        if self._apply_timer is not None:
            # Already queued - it will pick up the latest self._tokens.
            return
        self._apply_timer = QTimer(self)
        self._apply_timer.setSingleShot(True)
        self._apply_timer.timeout.connect(self._do_apply)
        self._apply_timer.start(0)

    def _do_apply(self) -> None:
        self._apply_timer = None
        self._apply()
        self._schedule_fanout()

    def _schedule_fanout(self, immediate: bool = False) -> None:
        """Emit :attr:`themeChanged` once, after the stylesheet has settled."""
        self._pending_tokens = self._tokens
        if immediate:
            self._flush_fanout()
            return
        if self._flush_timer is not None:
            self._flush_timer.stop()
        else:
            self._flush_timer = QTimer(self)
            self._flush_timer.setSingleShot(True)
            self._flush_timer.timeout.connect(self._flush_fanout)
        self._flush_timer.start(0)

    def _flush_fanout(self) -> None:
        if self._pending_tokens is None:
            return
        tokens = self._pending_tokens
        self._pending_tokens = None
        if tokens is not self._tokens:
            return
        self.themeChanged.emit(tokens)

    def _apply(self) -> None:
        """Push the palette + stylesheet onto the app, in one blocking pass.

        ``QApplication.setStyleSheet`` re-evaluates the sheet against the
        entire widget tree, and Qt will happily repaint intermediate states
        as each widget adopts the new rules. Both make the freeze look worse
        than it is, so:

        * repaints are suspended on every visible top-level window for the
          duration of the push (single repaint at the end);
        * a busy cursor is shown so the user knows something is happening;
        * the stylesheet string is cached, so a switch back to a previously
          used theme skips the formatting pass entirely.
        """
        windows = []
        try:
            for w in self._app.topLevelWindows():
                try:
                    if w.isVisible():
                        w.setUpdatesEnabled(False)
                        windows.append(w)
                except RuntimeError:
                    continue
        except RuntimeError:
            pass

        busy = False
        try:
            from PySide6.QtGui import QGuiApplication
            QGuiApplication.setOverrideCursor(Qt.CursorShape.BusyCursor)
            busy = True
        except Exception:
            pass

        try:
            self._app.setPalette(self._tokens.as_palette())
            self._app.setStyleSheet(_cached_stylesheet(self._tokens))
        finally:
            if busy:
                try:
                    from PySide6.QtGui import QGuiApplication
                    QGuiApplication.restoreOverrideCursor()
                except Exception:
                    pass
            for w in windows:
                try:
                    w.setUpdatesEnabled(True)
                    w.update()
                except RuntimeError:
                    continue
        # Dynamic-property widgets ([state="..."], severity chips, status
        # dots) need an explicit repolish; do it chunked on the event loop
        # so it never blocks a single frame.
        _schedule_repolish(self._app)


# ---------------------------------------------------------------------------
# Stylesheet cache
# ---------------------------------------------------------------------------

_STYLESHEET_CACHE: Dict[str, str] = {}


def _cached_stylesheet(t: ThemeTokens) -> str:
    """Return the rendered QSS for ``t``, memoised by (theme, accent)."""
    key = f"{t.key}:{t.accent}"
    sheet = _STYLESHEET_CACHE.get(key)
    if sheet is None:
        sheet = build_stylesheet(t)
        # Keep the cache bounded; the working set is small (a couple of
        # themes the user flips between) so a hard cap is fine.
        if len(_STYLESHEET_CACHE) > 8:
            _STYLESHEET_CACHE.clear()
        _STYLESHEET_CACHE[key] = sheet
    return sheet


# ---------------------------------------------------------------------------
# Chunked repolish (unchanged behaviour, still needed)
# ---------------------------------------------------------------------------

_REPOLISH_BATCH = 40
_REPOLISH_TOKEN = [0]


def _schedule_repolish(app) -> None:
    _REPOLISH_TOKEN[0] += 1
    token = _REPOLISH_TOKEN[0]

    try:
        candidates = app.allWidgets()
    except RuntimeError:
        return

    targets = []
    for w in candidates:
        try:
            if not w.isVisible():
                continue
            if not w.dynamicPropertyNames():
                continue
        except RuntimeError:
            continue
        targets.append(w)

    if not targets:
        return
    _repolish_batch(targets, 0, token)


def _repolish_batch(widgets, start: int, token: int) -> None:
    if token != _REPOLISH_TOKEN[0]:
        return
    end = min(start + _REPOLISH_BATCH, len(widgets))
    for i in range(start, end):
        w = widgets[i]
        try:
            w.style().unpolish(w)
            w.style().polish(w)
            w.update()
        except RuntimeError:
            continue
    if end < len(widgets):
        QTimer.singleShot(0, lambda: _repolish_batch(widgets, end, token))


def repolish_dynamic(app) -> None:
    """Kept for backwards compatibility - now schedules a chunked pass."""
    _schedule_repolish(app)


def apply_theme(app, theme_key: Optional[str] = None) -> ThemeManager:
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    manager = ThemeManager.instance(app)
    if theme_key:
        manager.set_theme(theme_key)
        # First apply is synchronous by design (see load_preferences).
        manager._do_apply()
    else:
        manager.load_preferences()
    return manager


def token_color(role: str, fallback: str = "#4f8cff") -> str:
    return getattr(ThemeManager.current(), role, fallback)