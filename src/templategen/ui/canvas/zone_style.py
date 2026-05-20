"""Compute per-zone visual styling (radius + fill color) for a variant."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from PySide6.QtGui import QColor

from templategen.model.enums import PlayerId
from templategen.model.main_objects import SpawnObject
from templategen.ui.canvas.zone_item import DEFAULT_RADIUS

if TYPE_CHECKING:
    from templategen.model.variant import Variant
    from templategen.model.zone import Zone


_PLAYER_COLOR: Final[dict[str, QColor]] = {
    PlayerId.PLAYER_1: QColor("#d04b4b"),  # red
    PlayerId.PLAYER_2: QColor("#3a78d6"),  # blue
    PlayerId.PLAYER_3: QColor("#e8703a"),  # orange
    PlayerId.PLAYER_4: QColor("#5ab84b"),  # green
    PlayerId.PLAYER_5: QColor("#a358cf"),  # purple
    PlayerId.PLAYER_6: QColor("#3fb8b8"),  # teal
    PlayerId.PLAYER_7: QColor("#e7b93a"),  # yellow
    PlayerId.PLAYER_8: QColor("#e58fc1"),  # pink
}

_TREASURE_LOW: Final[QColor] = QColor("#7a4a25")   # brown
_TREASURE_HIGH: Final[QColor] = QColor("#f4c542")  # golden yellow
_FALLBACK_COLOR: Final[QColor] = QColor("#666b75")


@dataclass(frozen=True)
class ZoneStyle:
    radius: float
    fill: QColor


def compute_zone_styles(variant: Variant) -> dict[str, ZoneStyle]:
    if not variant.zones:
        return {}

    radii = _compute_radii(variant)
    fills = _compute_fills(variant)
    return {z.name: ZoneStyle(radius=radii[z.name], fill=fills[z.name]) for z in variant.zones}


def _compute_radii(variant: Variant) -> dict[str, float]:
    sizes = [max(z.size, 0.0) for z in variant.zones]
    min_size = min((s for s in sizes if s > 0), default=1.0)
    radii: dict[str, float] = {}
    for zone in variant.zones:
        size = max(zone.size, min_size)
        scale = math.sqrt(size / min_size) if min_size > 0 else 1.0
        radii[zone.name] = DEFAULT_RADIUS * scale
    return radii


def _compute_fills(variant: Variant) -> dict[str, QColor]:
    spawn_for: dict[str, str] = {}
    treasure_total: dict[str, int] = {}
    for zone in variant.zones:
        spawn = _spawn_player(zone)
        if spawn is not None:
            spawn_for[zone.name] = spawn
        else:
            treasure_total[zone.name] = _zone_value(zone)

    if treasure_total:
        lo = min(treasure_total.values())
        hi = max(treasure_total.values())
    else:
        lo = hi = 0

    fills: dict[str, QColor] = {}
    for zone in variant.zones:
        if zone.name in spawn_for:
            fills[zone.name] = _PLAYER_COLOR.get(spawn_for[zone.name], _FALLBACK_COLOR)
            continue
        total = treasure_total.get(zone.name, 0)
        t = 0.0 if hi == lo else (total - lo) / (hi - lo)
        fills[zone.name] = _lerp_color(_TREASURE_LOW, _TREASURE_HIGH, t)
    return fills


def _spawn_player(zone: Zone) -> str | None:
    for mo in zone.mainObjects:
        if isinstance(mo, SpawnObject) and mo.spawn is not None:
            return mo.spawn
    return None


def _zone_value(zone: Zone) -> int:
    guarded = zone.guardedContentValue or 0
    unguarded = zone.unguardedContentValue or 0
    return guarded + unguarded


def _lerp_color(a: QColor, b: QColor, t: float) -> QColor:
    t = max(0.0, min(1.0, t))
    r = round(a.red() + (b.red() - a.red()) * t)
    g = round(a.green() + (b.green() - a.green()) * t)
    bl = round(a.blue() + (b.blue() - a.blue()) * t)
    return QColor(r, g, bl)
