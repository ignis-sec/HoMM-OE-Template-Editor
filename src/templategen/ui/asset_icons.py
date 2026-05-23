"""Centralized lookup for asset icons extracted from the game install."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtGui import QIcon

from templategen.infra.paths import interactable_icons_dir, item_icons_dir, spell_icons_dir
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


def spell_icon_path(catalog: ReferenceCatalog, sid: str) -> Path | None:
    spell = catalog.get_spell(sid)
    if spell is None:
        return None
    icon = spell.get("icon")
    if not isinstance(icon, str):
        return None
    path = spell_icons_dir() / f"{icon}.png"
    return path if path.exists() else None


def spell_qicon(catalog: ReferenceCatalog, sid: str) -> QIcon | None:
    path = spell_icon_path(catalog, sid)
    return QIcon(str(path)) if path is not None else None


def spell_listable(catalog: ReferenceCatalog, sid: str) -> ListableItem:
    spell = catalog.get_spell(sid)
    label: str | None = None
    if spell is not None:
        name = spell.get("name")
        if isinstance(name, str) and name and name != sid:
            label = f"{name}  ({sid})"
    return ListableItem(value=sid, label=label, icon=spell_qicon(catalog, sid))


def spell_listables(catalog: ReferenceCatalog) -> list[ListableItem]:
    """Every known spell as a ListableItem, sorted by SID."""
    return [spell_listable(catalog, sid) for sid in sorted(catalog.known_spell_sids())]


def interactable_icon_path(catalog: ReferenceCatalog, sid: str) -> Path | None:
    entry = catalog.get_interactable(sid)
    if entry is None:
        return None
    icon = entry.get("icon")
    if not isinstance(icon, str):
        return None
    path = interactable_icons_dir() / f"{icon}.png"
    return path if path.exists() else None


def interactable_qicon(catalog: ReferenceCatalog, sid: str) -> QIcon | None:
    path = interactable_icon_path(catalog, sid)
    return QIcon(str(path)) if path is not None else None


def interactable_listable(catalog: ReferenceCatalog, sid: str) -> ListableItem:
    entry = catalog.get_interactable(sid)
    label: str | None = None
    if entry is not None:
        name = entry.get("name")
        if isinstance(name, str) and name and name != sid:
            label = f"{name}  ({sid})"
    return ListableItem(value=sid, label=label, icon=interactable_qicon(catalog, sid))


def interactable_listables(catalog: ReferenceCatalog) -> list[ListableItem]:
    """Every known interactable as a ListableItem, sorted by SID."""
    return [interactable_listable(catalog, sid) for sid in sorted(catalog.known_interactable_sids())]


def sid_listable(catalog: ReferenceCatalog, sid: str) -> ListableItem:
    """Resolve any SID through whichever rich-data table it belongs to.

    Picks the first table that recognizes the SID (interactable → artifact → spell);
    falls back to a plain ListableItem if none does.
    """
    if catalog.get_interactable(sid) is not None:
        return interactable_listable(catalog, sid)
    if catalog.get_artifact(sid) is not None:
        return artifact_listable(catalog, sid)
    if catalog.get_spell(sid) is not None:
        return spell_listable(catalog, sid)
    return ListableItem(value=sid)


def sid_listables(catalog: ReferenceCatalog, sids: list[str]) -> list[ListableItem]:
    return [sid_listable(catalog, s) for s in sids]
