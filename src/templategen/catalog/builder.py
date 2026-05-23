"""Build a rich catalog snapshot from the game's `Core/` data folder."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Final, TypedDict

_log = logging.getLogger(__name__)

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
    artifact_sids: list[str]
    spell_sids: list[str]
    artifacts: dict[str, dict[str, Any]]
    spells: dict[str, dict[str, Any]]


SCHEMA_VERSION: Final[int] = 5

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


def build_snapshot(
    core_path: Path,
    *,
    item_icon_target_dir: Path | None = None,
    texture_root: Path | None = None,
) -> CatalogSnapshot:
    generator_root = _resolve_generator_root(core_path)
    core_root = generator_root.parent

    content_lists = _collect_content_lists(generator_root)
    content_pools = _collect_content_pools(generator_root)
    meta_objects = _collect_meta_objects(generator_root)
    biomes = _collect_biomes(generator_root)
    portals = _collect_portals(generator_root)
    resource_by_mine = _collect_resource_by_mine(generator_root)
    water_for_biome = _collect_water_for_biome(generator_root)
    artifacts = _collect_artifacts(core_root)
    spells = _collect_spells(core_root)

    if item_icon_target_dir is not None:
        textures = texture_root or (core_root.parent / "Assets" / "Texture2D")
        _copy_artifact_icons(artifacts, textures, item_icon_target_dir)

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
        artifact_sids=sorted(artifacts.keys()),
        spell_sids=sorted(spells.keys()),
        artifacts=artifacts,
        spells=spells,
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
    # Some game-data files ship with a UTF-8 BOM; utf-8-sig handles both forms.
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _collect_array_ids(directory: Path) -> list[str]:
    if not directory.is_dir():
        return []
    seen: set[str] = set()
    out: list[str] = []
    for path in sorted(directory.glob("*.json")):
        if path.name.startswith("test_"):
            continue
        try:
            data = _read_json(path)
        except (OSError, json.JSONDecodeError):
            continue
        entries = data.get("array") if isinstance(data, dict) else None
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            sid = entry.get("id")
            if isinstance(sid, str) and sid not in seen:
                seen.add(sid)
                out.append(sid)
    return out


_SPELL_FIELDS_TO_KEEP: Final[tuple[str, ...]] = (
    "icon",
    "school_",
    "rank",
    "usedOnMap",
    "isSpecialMagic",
    "normalMagicSid",
)


def _collect_spells(core_root: Path) -> dict[str, dict[str, Any]]:
    magics_dir = core_root / "DB" / "magics"
    locale = _load_localization(core_root, "magic.json")
    out: dict[str, dict[str, Any]] = {}
    if not magics_dir.is_dir():
        return out
    for path in sorted(magics_dir.glob("*.json")):
        if path.name.startswith("test_"):
            continue
        try:
            data = _read_json(path)
        except (OSError, json.JSONDecodeError):
            continue
        entries = data.get("array") if isinstance(data, dict) else None
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            sid = entry.get("id")
            if not isinstance(sid, str) or sid in out:
                continue
            payload: dict[str, Any] = {}
            for field in _SPELL_FIELDS_TO_KEEP:
                if field in entry:
                    payload[field] = entry[field]
            name_key = entry.get("name")
            if isinstance(name_key, str):
                payload["name_key"] = name_key
                payload["name"] = locale.get(name_key, name_key)
            desc = entry.get("description")
            if isinstance(desc, list):
                parts = [locale.get(d, "") for d in desc if isinstance(d, str)]
                payload["description_keys"] = [d for d in desc if isinstance(d, str)]
                payload["description"] = "\n\n".join(p for p in parts if p)
            elif isinstance(desc, str):
                payload["description_keys"] = [desc]
                payload["description"] = locale.get(desc, "")
            magic_type = entry.get("magicTypeDescription")
            if isinstance(magic_type, str) and magic_type.strip():
                payload["magic_type_key"] = magic_type
                payload["magic_type"] = locale.get(magic_type, magic_type)
            out[sid] = payload
    return out


def _load_localization(core_root: Path, file_name: str, language: str = "english") -> dict[str, str]:
    path = core_root / "Lang" / language / "texts" / file_name
    if not path.exists():
        return {}
    try:
        data = _read_json(path)
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    out: dict[str, str] = {}
    for entry in data.get("tokens") or []:
        if not isinstance(entry, dict):
            continue
        sid = entry.get("sid")
        text = entry.get("text")
        if isinstance(sid, str) and isinstance(text, str):
            out[sid] = text
    return out


_ARTIFACT_FIELDS_TO_KEEP: Final[tuple[str, ...]] = (
    "icon",
    "slot_",
    "rarity",
    "itemSet",
    "goodsValue",
)


def _collect_artifacts(core_root: Path) -> dict[str, dict[str, Any]]:
    items_dir = core_root / "DB" / "items" / "items"
    locale = _load_localization(core_root, "artifacts.json")
    out: dict[str, dict[str, Any]] = {}
    if not items_dir.is_dir():
        return out
    for path in sorted(items_dir.glob("*.json")):
        if path.name.startswith("test_"):
            continue
        try:
            data = _read_json(path)
        except (OSError, json.JSONDecodeError):
            continue
        entries = data.get("array") if isinstance(data, dict) else None
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            sid = entry.get("id")
            if not isinstance(sid, str) or sid in out:
                continue
            payload: dict[str, Any] = {}
            for field in _ARTIFACT_FIELDS_TO_KEEP:
                if field in entry:
                    payload[field] = entry[field]
            name_key = entry.get("name")
            desc_key = entry.get("description")
            if isinstance(name_key, str):
                payload["name_key"] = name_key
                payload["name"] = locale.get(name_key, name_key)
            if isinstance(desc_key, str):
                payload["description_key"] = desc_key
                payload["description"] = locale.get(desc_key, "")
            out[sid] = payload
    return out


def _read_png_size(path: Path) -> tuple[int, int] | None:
    """Parse the IHDR chunk to return (width, height) without loading the image."""
    try:
        with path.open("rb") as f:
            f.seek(16)  # 8-byte PNG sig + 4 length + 4 "IHDR"
            data = f.read(8)
    except OSError:
        return None
    if len(data) != 8:
        return None
    return (int.from_bytes(data[:4], "big"), int.from_bytes(data[4:], "big"))


def _resolve_icon_source(texture_root: Path, icon: str) -> Path | None:
    """Pick the best source PNG for an icon, preferring a `_0` variant when the
    base file is the 64x64 placeholder size."""
    base = texture_root / f"{icon}.png"
    if not base.exists():
        return None
    size = _read_png_size(base)
    if size == (64, 64):
        alt = texture_root / f"{icon}_0.png"
        if alt.exists():
            return alt
    return base


def _copy_artifact_icons(
    artifacts: dict[str, dict[str, Any]],
    texture_root: Path,
    target_dir: Path,
) -> None:
    """Copy each referenced artifact icon PNG into `target_dir`.

    Only files matching the `icon` field of an item are copied — the source dir holds
    8000+ images and we don't want to ship them all.
    """
    import shutil

    if not texture_root.is_dir():
        return
    target_dir.mkdir(parents=True, exist_ok=True)
    copied = 0
    missing: list[str] = []
    upscaled = 0
    for sid, payload in artifacts.items():
        icon = payload.get("icon")
        if not isinstance(icon, str):
            continue
        src = _resolve_icon_source(texture_root, icon)
        if src is None:
            missing.append(sid)
            continue
        if src.name != f"{icon}.png":
            upscaled += 1
        dst = target_dir / f"{icon}.png"
        shutil.copyfile(src, dst)
        copied += 1
    if missing:
        _log.warning(
            "%d artifact icon(s) missing from %s: %s...",
            len(missing),
            texture_root,
            missing[:5],
        )
    _log.info(
        "copied %d artifact icons (%d resolved to _0 variant) to %s",
        copied,
        upscaled,
        target_dir,
    )


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
