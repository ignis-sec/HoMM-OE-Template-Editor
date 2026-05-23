"""Centralized lookup for asset icons extracted from the game install."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtGui import QIcon

from templategen.infra.paths import item_icons_dir
from templategen.ui.widgets.listable import ListableItem

if TYPE_CHECKING:
    from pathlib import Path

    from templategen.catalog.catalog import ReferenceCatalog


def artifact_icon_path(catalog: ReferenceCatalog, sid: str) -> Path | None:
    artifact = catalog.get_artifact(sid)
    if artifact is None:
        return None
    icon = artifact.get("icon")
    if not isinstance(icon, str):
        return None
    path = item_icons_dir() / f"{icon}.png"
    return path if path.exists() else None


def artifact_qicon(catalog: ReferenceCatalog, sid: str) -> QIcon | None:
    path = artifact_icon_path(catalog, sid)
    return QIcon(str(path)) if path is not None else None


def artifact_listable(catalog: ReferenceCatalog, sid: str) -> ListableItem:
    """Build a richly-displayable ListableItem for a single artifact SID."""
    artifact = catalog.get_artifact(sid)
    label: str | None = None
    if artifact is not None:
        name = artifact.get("name")
        if isinstance(name, str) and name and name != sid:
            label = f"{name}  ({sid})"
    return ListableItem(value=sid, label=label, icon=artifact_qicon(catalog, sid))


def artifact_listables(catalog: ReferenceCatalog) -> list[ListableItem]:
    """Every known artifact as a ListableItem, sorted by SID."""
    return [artifact_listable(catalog, sid) for sid in sorted(catalog.known_artifact_sids())]
