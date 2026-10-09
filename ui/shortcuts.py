"""Keyboard shortcut registry.

Single source of truth for the app's key bindings. ``ShortcutsOverlay`` in
``ui.modals`` renders from this module, so the on-screen reference can never
drift from the key sequences that ``MainWindow._install_shortcuts`` is
actually wired up to.

Each section may describe a key range with a trailing ellipsis (``Ctrl+1…9``);
the reference sheet renders that notation as a single compact row.
"""
from __future__ import annotations

from typing import List, Tuple

# (section title, [(key sequence, description), ...])
ShortcutSection = Tuple[str, List[Tuple[str, str]]]

SHORTCUT_SECTIONS: List[ShortcutSection] = [
    ("Navigation", [
        ("Ctrl+1…9", "Jump straight to a page"),
        ("Ctrl+O", "Choose a folder to analyze"),
        ("?", "Show this shortcut sheet"),
        ("Esc", "Cancel a running scan / close an overlay"),
    ]),
    ("Analysis", [
        ("F5", "Start or restart a scan"),
        ("Ctrl+R", "Rescan the current folder"),
        ("Ctrl+L", "Focus the folder path field"),
    ]),
    ("Reports", [
        ("Ctrl+E", "Open the Reports page"),
        ("Ctrl+S", "Export the selected formats"),
        ("Ctrl+Shift+O", "Open the last export folder"),
    ]),
    ("Appearance", [
        ("Ctrl+T", "Toggle light / dark theme"),
        ("Ctrl+,", "Open Settings"),
    ]),
]
