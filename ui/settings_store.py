"""Shared analysis configuration for the UI layer.

The :class:`~folder_analyzer.models.AnalysisConfig` instance is edited live by
the Settings page, then copied into the scanner/analyzer when a scan starts.
Keeping it module-level means every page reads the same object without the
main window having to hand references around.
"""

from __future__ import annotations

import copy

from folder_analyzer.models import AnalysisConfig

_CONFIG = AnalysisConfig(
    folder_path="",
    top_n=30,
    include_hidden=False,
    detect_duplicates=True,
    tree_max_depth=3,
    largest_n=50,
    oldest_n=50,
    recent_n=50,
    deep_depth_threshold=6,
    junk_min_age_days=30,
)


def active_config() -> AnalysisConfig:
    """The live config edited by Settings and read by ``start_scan``."""
    return _CONFIG


def config_for_scan(folder_path: str) -> AnalysisConfig:
    """A snapshot of the live config bound to ``folder_path``.

    A copy is used so a scan keeps consistent settings even if the user keeps
    editing the config while the scan is running.
    """
    snapshot = copy.deepcopy(_CONFIG)
    snapshot.folder_path = folder_path
    return snapshot