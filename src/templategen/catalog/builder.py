"""Build a rich catalog snapshot from the game's `Core/` data folder."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Final, TypedDict

if TYPE_CHECKING:
    from pathlib import Path


class CatalogSnapshot(TypedDict):
    version: int
    generated_from: str
    generated_at: str
    sids: list[str]
    content_lists: dict[str, dict[str, Any]]
    content_pools: dict[str, dict[str, Any]]
    meta_objects: dict[str, dict[str, Any]]
    biomes: list[str]
    bonus_sids: list[str]
    building_constructions: list[str]
    portals: list[str]
    resource_by_mine: dict[str, str]
    water_for_biome: dict[str, str]


SCHEMA_VERSION: Final[int] = 2

_BONUS_SIDS: Final[list[str]] = [
    "add_bonus_hero_item",
    "add_bonus_hero_spell",
    "add_bonus_hero_stat",
    "add_bonus_hero_unit_multipler",
    "add_bonus_res",
]

_BUILDING_CONSTRUCTIONS: Final[list[str]] = [
    "default_buildings_construction",
    "poor_buildings_construction",
    "rich_buildings_construction",
    "extra_rich_buildings_construction",
    "ultra_rich_buildings_construction",
    "army_buildings_construction",
]


class CatalogBuildError(Exception):
    pass


def build_snapshot(core_path: Path) -> CatalogSnapshot:
    generator_root = _resolve_generator_root(core_path)

    content_lists = _collect_content_lists(generator_root)
    content_pools = _collect_content_pools(generator_root)
    meta_objects = _collect_meta_objects(generator_root)
    biomes = _collect_biomes(generator_root)
    portals = _collect_portals(generator_root)
    resource_by_mine = _collect_resource_by_mine(generator_root)
    water_for_biome = _collect_water_for_biome(generator_root)

    sids = sorted(_collect_sids(generator_root, content_lists, content_pools, meta_objects))

    return CatalogSnapshot(
        version=SCHEMA_VERSION,
        generated_from=str(core_path.resolve()),
        generated_at=datetime.now(UTC).isoformat(timespec="seconds"),
        sids=sids,
        content_lists=content_lists,
        content_pools=content_pools,
        meta_objects=meta_objects,
        biomes=biomes,
        bonus_sids=list(_BONUS_SIDS),
        building_constructions=list(_BUILDING_CONSTRUCTIONS),
        portals=portals,
        resource_by_mine=resource_by_mine,
        water_for_biome=water_for_biome,
    )


def write_snapshot(snapshot: CatalogSnapshot, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _resolve_generator_root(core_path: Path) -> Path:
    if (core_path / "generator").is_dir():
        return core_path / "generator"
    if core_path.name == "generator":
        return core_path
    raise CatalogBuildError(
        f"Expected a 'Core' folder containing 'generator/', or the 'generator' folder itself. Got: {core_path}"
    )


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _collect_content_lists(root: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for path in (root / "content_lists").glob("*.json"):
        data = _read_json(path)
        if not isinstance(data, list):
            continue
        for entry in data:
            if not isinstance(entry, dict):
                continue
            name = entry.get("name")
            if not isinstance(name, str):
                continue
            payload = {k: v for k, v in entry.items() if k != "name"}
            result[name] = payload
    return result


def _collect_content_pools(root: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for path in (root / "content_pools").rglob("*.json"):
        data = _read_json(path)
        if not isinstance(data, list):
            continue
        for entry in data:
            if not isinstance(entry, dict):
                continue
            name = entry.get("name")
            if not isinstance(name, str):
                continue
            payload = {k: v for k, v in entry.items() if k != "name"}
            result[name] = payload
    return result


def _collect_meta_objects(root: Path) -> dict[str, dict[str, Any]]:
    config_path = root / "generator_config.json"
    if not config_path.exists():
        return {}
    config = _read_json(config_path)
    result: dict[str, dict[str, Any]] = {}
    for entry in config.get("metaObjects", []):
        if not isinstance(entry, dict):
            continue
        sid = entry.get("sid")
        if isinstance(sid, str):
            result[sid] = {k: v for k, v in entry.items() if k != "sid"}
    return result


def _collect_biomes(root: Path) -> list[str]:
    env_path = root / "generator_environment_assets.json"
    if not env_path.exists():
        return []
    env = _read_json(env_path)
    biomes = env.get("biomes", []) if isinstance(env, dict) else []
    return [b["sid"] for b in biomes if isinstance(b, dict) and isinstance(b.get("sid"), str)]


def _collect_portals(root: Path) -> list[str]:
    config_path = root / "generator_config.json"
    if not config_path.exists():
        return []
    config = _read_json(config_path)
    portals = config.get("portals", []) if isinstance(config, dict) else []
    return [p for p in portals if isinstance(p, str)]


def _collect_resource_by_mine(root: Path) -> dict[str, str]:
    config_path = root / "generator_config.json"
    if not config_path.exists():
        return {}
    config = _read_json(config_path)
    out: dict[str, str] = {}
    for mapping in config.get("resourceByMine", []):
        if isinstance(mapping, dict):
            key, val = mapping.get("key"), mapping.get("val")
            if isinstance(key, str) and isinstance(val, str):
                out[key] = val
    return out


def _collect_water_for_biome(root: Path) -> dict[str, str]:
    config_path = root / "generator_config.json"
    if not config_path.exists():
        return {}
    config = _read_json(config_path)
    out: dict[str, str] = {}
    for mapping in config.get("waterForBiome", []):
        if isinstance(mapping, dict):
            key, val = mapping.get("key"), mapping.get("val")
            if isinstance(key, str) and isinstance(val, str):
                out[key] = val
    return out


def _collect_sids(
    root: Path,
    content_lists: dict[str, dict[str, Any]],
    content_pools: dict[str, dict[str, Any]],
    meta_objects: dict[str, dict[str, Any]],
) -> set[str]:
    sids: set[str] = set(meta_objects.keys())

    stats_path = root / "generator_stats_config.json"
    if stats_path.exists():
        stats = _read_json(stats_path)
        for sid in stats.get("statSids", []):
            if isinstance(sid, str):
                sids.add(sid)

    for mine_sid, resource_sid in _collect_resource_by_mine(root).items():
        sids.add(mine_sid)
        sids.add(resource_sid)

    for payload in content_lists.values():
        for entry in payload.get("content", []):
            if isinstance(entry, dict) and isinstance(entry.get("sid"), str):
                sids.add(entry["sid"])

    for payload in content_pools.values():
        for group in payload.get("groups", []):
            if not isinstance(group, dict):
                continue
            for item in group.get("content", []) or []:
                if isinstance(item, dict) and isinstance(item.get("sid"), str):
                    sids.add(item["sid"])
        for ban in payload.get("bans", []) or []:
            if isinstance(ban, dict) and isinstance(ban.get("sid"), str):
                sids.add(ban["sid"])

    return sids
