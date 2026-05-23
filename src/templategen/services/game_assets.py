"""Find, extract from, and pull icons out of a Heroes of Might & Magic Olden Era install."""

from __future__ import annotations

import logging
import platform
import shutil
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

_log = logging.getLogger(__name__)

# Default Steam install locations per platform. The Windows folder name uses '&' and the
# Linux folder name uses 'and'; both forms appear in the wild so we probe several.
_DEFAULT_PATHS_WINDOWS: tuple[str, ...] = (
    r"C:\Program Files (x86)\Steam\steamapps\common\Heroes of Might & Magic Olden Era",
    r"C:\Program Files (x86)\Steam\steamapps\common\Heroes of Might and Magic Olden Era",
    r"C:\Program Files\Steam\steamapps\common\Heroes of Might & Magic Olden Era",
)
_DEFAULT_PATHS_LINUX: tuple[str, ...] = (
    "~/.steam/steam/steamapps/common/Heroes of Might and Magic Olden Era",
    "~/.steam/steam/steamapps/common/Heroes of Might & Magic Olden Era",
    "~/.local/share/Steam/steamapps/common/Heroes of Might and Magic Olden Era",
)
_DEFAULT_PATHS_MAC: tuple[str, ...] = (
    "~/Library/Application Support/Steam/steamapps/common/Heroes of Might and Magic Olden Era",
)


def default_game_paths() -> list[Path]:
    system = platform.system()
    if system == "Windows":
        return [Path(p) for p in _DEFAULT_PATHS_WINDOWS]
    if system == "Darwin":
        return [Path(p).expanduser() for p in _DEFAULT_PATHS_MAC]
    return [Path(p).expanduser() for p in _DEFAULT_PATHS_LINUX]


def is_game_install(path: Path | None) -> bool:
    """A game install must contain HeroesOldenEra_Data/app.info."""
    if path is None:
        return False
    return (path / "HeroesOldenEra_Data" / "app.info").is_file()


def find_game_install() -> Path | None:
    """Return the first probed default path that looks like a valid install, or None."""
    for candidate in default_game_paths():
        if is_game_install(candidate):
            return candidate
    return None


def game_data_dir(game_install: Path) -> Path:
    return game_install / "HeroesOldenEra_Data"


def core_zip_path(game_install: Path) -> Path:
    return game_data_dir(game_install) / "StreamingAssets" / "Core.zip"


def extract_core_zip(game_install: Path, target_dir: Path) -> Path:
    """Unzip Core.zip into `target_dir/Core`. Returns the resulting Core/ root."""
    src = core_zip_path(game_install)
    if not src.is_file():
        raise FileNotFoundError(f"Core.zip not found at {src}")
    # Wipe any previous extraction so stale files don't linger across game updates.
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(src) as zf:
        zf.extractall(target_dir)
    # Resolve the inner Core/ folder; the zip may root at "Core/" or its contents directly.
    inner = target_dir / "Core"
    if inner.is_dir():
        return inner
    return target_dir


# Unity Texture2D format enum value for the hi-res RGBA BC7 textures used by Olden Era's
# canonical artifact icons. Duplicate placeholders in the same bundle share the texture's
# `m_Name` but use legacy formats (10 = DXT5, 25 = BC7 8x8 block-compressed at 64x64);
# picking by m_TextureFormat is the deterministic, source-based way to disambiguate
# without comparing rendered image sizes. Verified across all 127 duplicate-set artifacts
# in the v1.0 game data — the BC7 (fmt 12) texture is always the correct hi-res source.
_PREFERRED_TEXTURE_FORMAT: Final[int] = 12


def extract_named_textures(
    game_install: Path,
    icon_names: Iterable[str],
    target_dir: Path,
    *,
    progress: Callable[[int, int], None] | None = None,
    kind: str = "icons",
    prefer_size: tuple[int, int] | None = None,
) -> tuple[int, list[str]]:
    """Walk Texture2D objects in the game's _Data bundles, save matches as PNGs.

    Picker rules when a name has multiple candidates:
      - if `prefer_size` is set, pick a candidate whose decoded image matches that size
        (used for the 64x64 interactable map icons, which share names with larger
        atlases / hi-res variants we don't want here);
      - otherwise prefer m_TextureFormat == 12 (BC7) — the canonical hi-res source for
        artifacts and spells;
      - in either case, fall back to the first candidate when nothing matches.

    Returns (saved_count, missing_icon_names).
    """
    import UnityPy  # type: ignore[import-untyped]

    data_dir = game_data_dir(game_install)
    if not data_dir.is_dir():
        raise FileNotFoundError(f"game data folder missing: {data_dir}")

    target_dir.mkdir(parents=True, exist_ok=True)
    wanted = {name for name in icon_names if isinstance(name, str) and name}
    if not wanted:
        return 0, []

    # For each icon name, keep every (texture_format, parsed_data) candidate we find.
    # We defer .image decoding to after picking so we only decompress the texture we
    # actually save.
    candidates: dict[str, list[tuple[int, object]]] = {name: [] for name in wanted}
    env = UnityPy.load(str(data_dir))
    for obj in env.objects:
        if obj.type.name != "Texture2D":
            continue
        data = obj.read()
        name = getattr(data, "m_Name", None) or getattr(data, "name", None) or ""
        if name not in candidates:
            continue
        fmt = getattr(data, "m_TextureFormat", -1)
        try:
            fmt_int = int(fmt)
        except (TypeError, ValueError):
            fmt_int = -1
        candidates[name].append((fmt_int, data))

    saved = 0
    preferred_picks = 0
    found: set[str] = set()
    total = len(wanted)
    for name in sorted(wanted):
        options = candidates.get(name, [])
        if not options:
            continue
        chosen, picked_preferred = _pick_texture(options, prefer_size)
        if picked_preferred:
            preferred_picks += 1
        try:
            image = chosen.image
        except Exception as exc:  # pragma: no cover - defensive
            _log.warning("could not decode texture %s: %s", name, exc)
            continue
        image.save(target_dir / f"{name}.png")
        found.add(name)
        saved += 1
        if progress is not None:
            progress(saved, total)

    rule = f"size={prefer_size}" if prefer_size is not None else f"m_TextureFormat={_PREFERRED_TEXTURE_FORMAT}"
    _log.info(
        "extracted %d %s (%d disambiguated by preferring %s)",
        saved,
        kind,
        preferred_picks,
        rule,
    )
    return saved, sorted(set(icon_names) - found)


def _pick_texture(
    options: list[tuple[int, object]],
    prefer_size: tuple[int, int] | None,
) -> tuple[object, bool]:
    """Pick the best Texture2D candidate from a same-name set.

    Returns (chosen_texture_data, used_preferred_rule).
    """
    if prefer_size is not None:
        for _fmt, data in options:
            try:
                if data.image.size == prefer_size:
                    return data, True
            except Exception:
                continue
        return options[0][1], False
    bc7 = next((data for fmt, data in options if fmt == _PREFERRED_TEXTURE_FORMAT), None)
    if bc7 is not None:
        return bc7, True
    return options[0][1], False
