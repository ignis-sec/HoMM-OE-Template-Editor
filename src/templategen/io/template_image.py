"""Render a Template's variant graph as a stylized PNG using bundled tile artwork."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Final

from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor, QImage, QPainter, QPen

from templategen.model.enums import ConnectionType
from templategen.model.main_objects import CityObject, SpawnObject

if TYPE_CHECKING:
    from templategen.model.template import Template
    from templategen.model.variant import Variant
    from templategen.model.zone import Zone


_IMG_DIR: Final[Path] = Path(__file__).resolve().parent.parent / "img"
_PADDING: Final[int] = 68
_CONNECTION_COLOR: Final[QColor] = QColor("#350f13")
_CONNECTION_WIDTH: Final[int] = 3


def template_png_path(rmg_path: Path) -> Path:
    name = rmg_path.name
    suffix = ".rmg.json"
    stem = name[: -len(suffix)] if name.endswith(suffix) else rmg_path.stem
    return rmg_path.with_name(f"{stem}.png")


def render_template_png(template: Template, output: Path, *, variant_index: int = 0) -> None:
    if not template.variants:
        return
    idx = variant_index if 0 <= variant_index < len(template.variants) else 0
    variant = template.variants[idx]
    if not variant.zones:
        return

    bg = QImage(str(_IMG_DIR / "bg.png"))
    if bg.isNull():
        raise FileNotFoundError(f"background image missing: {_IMG_DIR / 'bg.png'}")

    image_cache: dict[str, QImage] = {}

    def load(name: str) -> QImage:
        if name not in image_cache:
            image_cache[name] = QImage(str(_IMG_DIR / name))
        return image_cache[name]

    positions = _scaled_positions(variant, bg.width(), bg.height())
    base_image, overlay_image = _zone_images(variant)

    canvas = QImage(bg.size(), QImage.Format.Format_ARGB32)
    canvas.fill(0)
    painter = QPainter(canvas)
    try:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawImage(0, 0, bg)

        pen = QPen(_CONNECTION_COLOR)
        pen.setWidth(_CONNECTION_WIDTH)
        painter.setPen(pen)
        for conn in variant.connections:
            if conn.connectionType not in (ConnectionType.DIRECT, ConnectionType.DEFAULT, ConnectionType.PORTAL):
                continue
            a = positions.get(conn.from_)
            b = positions.get(conn.to)
            if a is None or b is None:
                continue
            painter.drawLine(a, b)

        for zone in variant.zones:
            pos = positions.get(zone.name)
            if pos is None:
                continue
            _draw_centered(painter, load(base_image[zone.name]), pos)
            overlay = overlay_image.get(zone.name)
            if overlay is not None:
                _draw_centered(painter, load(overlay), pos)
    finally:
        painter.end()

    canvas.save(str(output), "PNG")


def _draw_centered(painter: QPainter, img: QImage, pos: QPointF) -> None:
    if img.isNull():
        return
    painter.drawImage(
        QPointF(pos.x() - img.width() / 2, pos.y() - img.height() / 2),
        img,
    )


def _scaled_positions(variant: Variant, bg_w: int, bg_h: int) -> dict[str, QPointF]:
    from templategen.ui.canvas.layout import compute_layout

    positions = compute_layout(variant)
    if not positions:
        return {}

    xs = [p[0] for p in positions.values()]
    ys = [p[1] for p in positions.values()]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span_x = (max_x - min_x) or 1.0
    span_y = (max_y - min_y) or 1.0

    avail_x = bg_w - 2 * _PADDING
    avail_y = bg_h - 2 * _PADDING
    cx = bg_w / 2
    cy = bg_h / 2

    if len(positions) == 1:
        only = next(iter(positions))
        return {only: QPointF(cx, cy)}

    return {
        name: QPointF(
            _PADDING + (p[0] - min_x) / span_x * avail_x,
            _PADDING + (p[1] - min_y) / span_y * avail_y,
        )
        for name, p in positions.items()
    }


def _zone_images(variant: Variant) -> tuple[dict[str, str], dict[str, str]]:
    base: dict[str, str] = {}
    overlay: dict[str, str] = {}

    nonspawn: list[tuple[str, int]] = []
    for zone in variant.zones:
        spawn = _spawn_tile(zone)
        if spawn is not None:
            base[zone.name] = spawn
        else:
            nonspawn.append((zone.name, _content_value(zone)))

    nonspawn.sort(key=lambda kv: kv[1])
    n = len(nonspawn)
    for i, (name, _value) in enumerate(nonspawn):
        base[name] = _tier_tile(i, n)

    for zone in variant.zones:
        has_spawn = any(isinstance(mo, SpawnObject) for mo in zone.mainObjects)
        has_city = any(isinstance(mo, CityObject) for mo in zone.mainObjects)
        if has_city and not has_spawn:
            overlay[zone.name] = "town.png"

    return base, overlay


def _spawn_tile(zone: Zone) -> str | None:
    for mo in zone.mainObjects:
        if isinstance(mo, SpawnObject) and mo.spawn is not None:
            digit = str(mo.spawn.value).removeprefix("Player")
            return f"{digit}.png"
    return None


def _tier_tile(index: int, total: int) -> str:
    if total <= 1:
        return "z-mid.png"
    rank = index / (total - 1)
    if rank <= 0.3:
        return "z-poor.png"
    if rank >= 0.7:
        return "z-rich.png"
    return "z-mid.png"


def _content_value(zone: Zone) -> int:
    g = zone.guardedContentValue or 0
    u = zone.unguardedContentValue or 0
    gpa = zone.guardedContentValuePerArea or 0
    upa = zone.unguardedContentValuePerArea or 0
    return g + u + gpa + upa
