"""User-data paths: where the editor stores game-derived catalog + icons."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QStandardPaths


def app_data_root() -> Path:
    """Per-user app data dir (created if missing). Linux: ~/.local/share/<org>/<app>/."""
    root = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation))
    root.mkdir(parents=True, exist_ok=True)
    return root


def extracted_core_dir() -> Path:
    return app_data_root() / "Core"


def catalog_json_path() -> Path:
    return app_data_root() / "catalog.json"


def item_icons_dir() -> Path:
    return app_data_root() / "items"


def spell_icons_dir() -> Path:
    return app_data_root() / "magics"


def interactable_icons_dir() -> Path:
    return app_data_root() / "interactables"


def resource_icons_dir() -> Path:
    return app_data_root() / "resources"
