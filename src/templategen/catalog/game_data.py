"""GameDataCatalog — loads the rich snapshot from data/catalog.json."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QObject, Signal

from templategen.catalog.builder import SCHEMA_VERSION
from templategen.catalog.catalog import ReferenceCatalog
from templategen.infra.paths import catalog_json_path

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

_log = logging.getLogger(__name__)


class GameDataCatalog(QObject, ReferenceCatalog):
    changed = Signal()

    def __init__(self, snapshot_path: Path | None = None) -> None:
        super().__init__()
        self._path = snapshot_path if snapshot_path is not None else catalog_json_path()
        self._reset()
        self.reload()

    @property
    def snapshot_path(self) -> Path:
        return self._path

    def is_loaded(self) -> bool:
        return bool(self._sids or self._content_lists or self._content_pools)

    def reload(self) -> None:
        if not self._path.exists():
            self._reset()
            self.changed.emit()
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            _log.warning("catalog snapshot is unreadable: %s", self._path)
            self._reset()
            self.changed.emit()
            return

        version = data.get("version")
        if version != SCHEMA_VERSION:
            _log.warning(
                "catalog snapshot version %s does not match expected %s — treating as empty",
                version,
                SCHEMA_VERSION,
            )
            self._reset()
            self.changed.emit()
            return

        self._sids = list(data.get("sids", []))
        self._content_lists = dict(data.get("content_lists", {}))
        self._content_pools = dict(data.get("content_pools", {}))
        self._meta_objects = dict(data.get("meta_objects", {}))
        self._biomes = list(data.get("biomes", []))
        self._bonus_sids = list(data.get("bonus_sids", []))
        self._building_constructions = list(data.get("building_constructions", []))
        self._portals = list(data.get("portals", []))
        self._resource_by_mine = dict(data.get("resource_by_mine", {}))
        self._water_for_biome = dict(data.get("water_for_biome", {}))
        self._artifact_sids = list(data.get("artifact_sids", []))
        self._spell_sids = list(data.get("spell_sids", []))
        self._artifacts = dict(data.get("artifacts", {}))
        self._build_indices()
        self.changed.emit()

    def _reset(self) -> None:
        self._sids: list[str] = []
        self._content_lists: dict[str, dict[str, Any]] = {}
        self._content_pools: dict[str, dict[str, Any]] = {}
        self._meta_objects: dict[str, dict[str, Any]] = {}
        self._biomes: list[str] = []
        self._bonus_sids: list[str] = []
        self._building_constructions: list[str] = []
        self._portals: list[str] = []
        self._resource_by_mine: dict[str, str] = {}
        self._water_for_biome: dict[str, str] = {}
        self._artifact_sids: list[str] = []
        self._spell_sids: list[str] = []
        self._artifacts: dict[str, dict[str, Any]] = {}
        self._sid_in_lists: dict[str, list[str]] = {}
        self._sid_in_pool_content: dict[str, list[str]] = {}
        self._sid_produced_by_pools: dict[str, list[str]] = {}
        self._sid_banned_in_pools: dict[str, list[str]] = {}
        self._list_used_by_pools: dict[str, list[str]] = {}

    def _build_indices(self) -> None:
        self._sid_in_lists = {}
        self._sid_in_pool_content = {}
        self._sid_produced_by_pools = {}
        self._sid_banned_in_pools = {}
        self._list_used_by_pools = {}

        for list_name, list_data in self._content_lists.items():
            for entry in list_data.get("content", []) or []:
                if isinstance(entry, dict) and isinstance(entry.get("sid"), str):
                    self._sid_in_lists.setdefault(entry["sid"], []).append(list_name)

        for pool_name, pool_data in self._content_pools.items():
            direct_sids: set[str] = set()
            produced_sids: set[str] = set()
            for group in pool_data.get("groups", []) or []:
                if not isinstance(group, dict):
                    continue
                for entry in group.get("content", []) or []:
                    if isinstance(entry, dict) and isinstance(entry.get("sid"), str):
                        direct_sids.add(entry["sid"])
                        produced_sids.add(entry["sid"])
                for list_name in group.get("includeLists", []) or []:
                    if not isinstance(list_name, str):
                        continue
                    self._list_used_by_pools.setdefault(list_name, []).append(pool_name)
                    list_data = self._content_lists.get(list_name)
                    if not list_data:
                        continue
                    for entry in list_data.get("content", []) or []:
                        if isinstance(entry, dict) and isinstance(entry.get("sid"), str):
                            produced_sids.add(entry["sid"])

            for sid in direct_sids:
                self._sid_in_pool_content.setdefault(sid, []).append(pool_name)
            for sid in produced_sids:
                self._sid_produced_by_pools.setdefault(sid, []).append(pool_name)

            for ban in pool_data.get("bans", []) or []:
                if isinstance(ban, dict) and isinstance(ban.get("sid"), str):
                    self._sid_banned_in_pools.setdefault(ban["sid"], []).append(pool_name)

    # ── flat lookups ─────────────────────────────────────────────────────
    def known_sids(self) -> Sequence[str]:
        return self._sids

    def known_content_lists(self) -> Sequence[str]:
        return list(self._content_lists.keys())

    def known_content_pools(self) -> Sequence[str]:
        return list(self._content_pools.keys())

    def known_biomes(self) -> Sequence[str]:
        return self._biomes

    def known_bonus_sids(self) -> Sequence[str]:
        return self._bonus_sids

    def known_building_constructions(self) -> Sequence[str]:
        return self._building_constructions

    def known_portals(self) -> Sequence[str]:
        return self._portals

    def known_meta_object_sids(self) -> Sequence[str]:
        return list(self._meta_objects.keys())

    def known_artifact_sids(self) -> Sequence[str]:
        return self._artifact_sids

    def known_spell_sids(self) -> Sequence[str]:
        return self._spell_sids

    def get_artifact(self, sid: str) -> dict[str, Any] | None:
        return self._artifacts.get(sid)

    # ── detail lookups ───────────────────────────────────────────────────
    def get_content_list(self, name: str) -> dict[str, Any] | None:
        return self._content_lists.get(name)

    def get_content_pool(self, name: str) -> dict[str, Any] | None:
        return self._content_pools.get(name)

    def get_meta_object(self, sid: str) -> dict[str, Any] | None:
        return self._meta_objects.get(sid)

    def resource_for_mine(self, mine_sid: str) -> str | None:
        return self._resource_by_mine.get(mine_sid)

    def water_for_biome(self, biome: str) -> str | None:
        return self._water_for_biome.get(biome)

    # ── reverse lookups ──────────────────────────────────────────────────
    def lists_containing(self, sid: str) -> Sequence[str]:
        return self._sid_in_lists.get(sid, [])

    def pools_with_direct_sid(self, sid: str) -> Sequence[str]:
        return self._sid_in_pool_content.get(sid, [])

    def pools_producing(self, sid: str) -> Sequence[str]:
        return self._sid_produced_by_pools.get(sid, [])

    def pools_banning(self, sid: str) -> Sequence[str]:
        return self._sid_banned_in_pools.get(sid, [])

    def pools_using_list(self, list_name: str) -> Sequence[str]:
        return self._list_used_by_pools.get(list_name, [])
