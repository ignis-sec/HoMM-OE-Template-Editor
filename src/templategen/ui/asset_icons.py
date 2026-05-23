"""Centralized lookup for asset icons extracted from the game install."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtGui import QIcon

from templategen.infra.paths import (
    fraction_icons_dir,
    interactable_icons_dir,
    item_icons_dir,
    resource_icons_dir,
    spell_icons_dir,
)
from templategen.ui.widgets.listable import ListableItem

if TYPE_CHECKING:
    from pathlib import Path

    from templategen.catalog.catalog import ReferenceCatalog


_qicon_cache: dict[str, QIcon] = {}


def _cached_qicon(path: Path) -> QIcon:
    key = str(path)
    icon = _qicon_cache.get(key)
    if icon is None:
        icon = QIcon(key)
        _qicon_cache[key] = icon
    return icon


def artifact_icon_path(catalog: ReferenceCatalog, sid: str) -> Path | None:
    artifact = catalog.get_artifact(sid)
    if artifact is None:
        return None
    icon = artifact.get("icon")
    if not isinstance(icon, str):
        return None
    path = item_icons_dir() / f"{icon.lower()}.png"
    return path if path.exists() else None


def artifact_qicon(catalog: ReferenceCatalog, sid: str) -> QIcon | None:
    path = artifact_icon_path(catalog, sid)
    return _cached_qicon(path) if path is not None else None


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
    """Every known artifact as a ListableItem, sorted by display name."""
    items = [artifact_listable(catalog, sid) for sid in catalog.known_artifact_sids()]
    items.sort(key=lambda i: i.display.casefold())
    return items


def spell_icon_path(catalog: ReferenceCatalog, sid: str) -> Path | None:
    spell = catalog.get_spell(sid)
    if spell is None:
        return None
    icon = spell.get("icon")
    if not isinstance(icon, str):
        return None
    path = spell_icons_dir() / f"{icon.lower()}.png"
    return path if path.exists() else None


def spell_qicon(catalog: ReferenceCatalog, sid: str) -> QIcon | None:
    path = spell_icon_path(catalog, sid)
    return _cached_qicon(path) if path is not None else None


def spell_listable(catalog: ReferenceCatalog, sid: str) -> ListableItem:
    spell = catalog.get_spell(sid)
    label: str | None = None
    if spell is not None:
        name = spell.get("name")
        if isinstance(name, str) and name and name != sid:
            label = f"{name}  ({sid})"
    return ListableItem(value=sid, label=label, icon=spell_qicon(catalog, sid))


def spell_listables(catalog: ReferenceCatalog) -> list[ListableItem]:
    """Every known spell as a ListableItem, sorted by display name."""
    items = [spell_listable(catalog, sid) for sid in catalog.known_spell_sids()]
    items.sort(key=lambda i: i.display.casefold())
    return items


def interactable_icon_path(catalog: ReferenceCatalog, sid: str) -> Path | None:
    entry = catalog.get_interactable(sid)
    if entry is None:
        return None
    icon = entry.get("icon")
    if not isinstance(icon, str):
        return None
    path = interactable_icons_dir() / f"{icon.lower()}.png"
    return path if path.exists() else None


def interactable_qicon(catalog: ReferenceCatalog, sid: str) -> QIcon | None:
    path = interactable_icon_path(catalog, sid)
    return _cached_qicon(path) if path is not None else None


def interactable_listable(catalog: ReferenceCatalog, sid: str) -> ListableItem:
    entry = catalog.get_interactable(sid)
    label: str | None = None
    if entry is not None:
        name = entry.get("name")
        if isinstance(name, str) and name and name != sid:
            label = f"{name}  ({sid})"
    return ListableItem(value=sid, label=label, icon=interactable_qicon(catalog, sid))


def interactable_listables(catalog: ReferenceCatalog) -> list[ListableItem]:
    """Every known interactable as a ListableItem, sorted by display name."""
    items = [interactable_listable(catalog, sid) for sid in catalog.known_interactable_sids()]
    items.sort(key=lambda i: i.display.casefold())
    return items


def resource_icon_path(catalog: ReferenceCatalog, sid: str) -> Path | None:
    entry = catalog.get_resource(sid)
    if entry is None:
        return None
    icon = entry.get("icon")
    if not isinstance(icon, str):
        return None
    path = resource_icons_dir() / f"{icon.lower()}.png"
    return path if path.exists() else None


def resource_qicon(catalog: ReferenceCatalog, sid: str) -> QIcon | None:
    path = resource_icon_path(catalog, sid)
    return _cached_qicon(path) if path is not None else None


def resource_listable(catalog: ReferenceCatalog, sid: str) -> ListableItem:
    entry = catalog.get_resource(sid)
    label: str | None = None
    if entry is not None:
        name = entry.get("name")
        if isinstance(name, str) and name and name != sid:
            label = f"{name}  ({sid})"
    return ListableItem(value=sid, label=label, icon=resource_qicon(catalog, sid))


def resource_listables(catalog: ReferenceCatalog) -> list[ListableItem]:
    """Every known resource as a ListableItem, sorted by display name."""
    items = [resource_listable(catalog, sid) for sid in catalog.known_resource_sids()]
    items.sort(key=lambda i: i.display.casefold())
    return items


def fraction_icon_path(fraction: str) -> Path | None:
    path = fraction_icons_dir() / f"fraction_{fraction.lower()}.png"
    return path if path.exists() else None


def fraction_qicon(fraction: str) -> QIcon | None:
    path = fraction_icon_path(fraction)
    return _cached_qicon(path) if path is not None else None


def fraction_listable(fraction: str) -> ListableItem:
    label = fraction[:1].upper() + fraction[1:]
    return ListableItem(value=fraction, label=label, icon=fraction_qicon(fraction))


def fraction_listables(catalog: ReferenceCatalog) -> list[ListableItem]:
    items = [fraction_listable(f) for f in catalog.known_fractions()]
    items.sort(key=lambda i: i.display.casefold())
    return items


def sid_listable(catalog: ReferenceCatalog, sid: str) -> ListableItem:
    """Resolve any SID through whichever rich-data table it belongs to.

    Tries each known asset table in turn; falls back to a plain ListableItem if none
    recognizes the SID.
    """
    if catalog.get_interactable(sid) is not None:
        return interactable_listable(catalog, sid)
    if catalog.get_resource(sid) is not None:
        return resource_listable(catalog, sid)
    if catalog.get_artifact(sid) is not None:
        return artifact_listable(catalog, sid)
    if catalog.get_spell(sid) is not None:
        return spell_listable(catalog, sid)
    return ListableItem(value=sid)


def sid_listables(catalog: ReferenceCatalog, sids: list[str]) -> list[ListableItem]:
    items = [sid_listable(catalog, s) for s in sids]
    items.sort(key=lambda i: i.display.casefold())
    return items


def content_sid_listables(catalog: ReferenceCatalog) -> list[ListableItem]:
    """SIDs valid for ContentItem / LimitItem fields: interactables + resources +
    generic meta-objects (random pickups etc.). Artifacts, spells, and bonus SIDs are
    excluded because they have their own dedicated dropdowns."""
    exclude = (
        set(catalog.known_artifact_sids())
        | set(catalog.known_spell_sids())
        | set(catalog.known_bonus_sids())
    )
    seen: set[str] = set()
    items: list[ListableItem] = []
    for sid in catalog.known_interactable_sids():
        if sid in exclude or sid in seen:
            continue
        seen.add(sid)
        items.append(interactable_listable(catalog, sid))
    for sid in catalog.known_resource_sids():
        if sid in exclude or sid in seen:
            continue
        seen.add(sid)
        items.append(resource_listable(catalog, sid))
    for sid in catalog.known_sids():
        if sid in exclude or sid in seen:
            continue
        seen.add(sid)
        items.append(sid_listable(catalog, sid))
    items.sort(key=lambda i: i.display.casefold())
    return items
