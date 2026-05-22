"""GraphScene — binds the current Variant to draggable ZoneItems and EdgeItems."""

from typing import Final

from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QGraphicsScene

from templategen.model.variant import Variant
from templategen.model.zone import Zone
from templategen.services.session import EditorSession
from templategen.ui.canvas.connection_item import EdgeItem
from templategen.ui.canvas.layout import compute_layout
from templategen.ui.canvas.zone_item import ZoneItem
from templategen.ui.canvas.zone_style import compute_zone_styles

_SCENE_SIZE: Final[float] = 1200.0
_LAYOUT_SCALE: Final[float] = 500.0
_PARALLEL_SPACING: Final[float] = 12.0


class GraphScene(QGraphicsScene):
    def __init__(self, session: EditorSession) -> None:
        super().__init__()
        self._session = session
        self._zone_items: dict[str, ZoneItem] = {}
        self._pending_positions: dict[str, QPointF] = {}

        self.setSceneRect(-_SCENE_SIZE / 2, -_SCENE_SIZE / 2, _SCENE_SIZE, _SCENE_SIZE)

        session.template_changed.connect(self.rebuild)
        session.current_variant_changed.connect(self.rebuild)
        session.model_object_changed.connect(self._refresh_for)
        self.selectionChanged.connect(self._forward_selection)

        self.rebuild()

    @property
    def session(self) -> EditorSession:
        return self._session

    @property
    def current_variant(self) -> Variant | None:
        template = self._session.template
        if not template or not template.variants:
            return None
        idx = self._session.current_variant_index
        if not 0 <= idx < len(template.variants):
            return None
        return template.variants[idx]

    @property
    def zone_items(self) -> dict[str, ZoneItem]:
        return dict(self._zone_items)

    def stage_position(self, zone_name: str, scene_pos: QPointF) -> None:
        self._pending_positions[zone_name] = QPointF(scene_pos)

    def rebuild(self) -> None:
        prior_positions = {name: item.pos() for name, item in self._zone_items.items()}
        loaded_positions: dict[str, tuple[float, float]] = {}
        if not prior_positions:
            # On the first rebuild after load() the scene has no items yet, so prior_positions
            # is empty. Consume any positions restored from the sibling PNG metadata here.
            consume = getattr(self._session, "consume_loaded_positions", None)
            if callable(consume):
                loaded_positions = consume()
        self.clear()
        self._zone_items.clear()

        variant = self.current_variant
        if variant is None:
            return

        styles = compute_zone_styles(variant)
        layout_positions = compute_layout(variant) if variant.zones else {}

        for zone in variant.zones:
            style = styles[zone.name]
            item = ZoneItem(zone, radius=style.radius, fill=style.fill)
            if zone.name in self._pending_positions:
                item.setPos(self._pending_positions.pop(zone.name))
            elif zone.name in prior_positions:
                item.setPos(prior_positions[zone.name])
            elif zone.name in loaded_positions:
                lx, ly = loaded_positions[zone.name]
                item.setPos(QPointF(lx, ly))
            else:
                x, y = layout_positions[zone.name]
                item.setPos(x * _LAYOUT_SCALE, y * _LAYOUT_SCALE)
            self.addItem(item)
            self._zone_items[zone.name] = item

        offsets_by_id = _parallel_offsets(variant.connections)
        for conn in variant.connections:
            source = self._zone_items.get(conn.from_)
            target = self._zone_items.get(conn.to)
            if source is None or target is None:
                continue
            edge = EdgeItem(conn, source, target, parallel_offset=offsets_by_id.get(id(conn), 0.0))
            self.addItem(edge)

        self.update()

    def _forward_selection(self) -> None:
        items = self.selectedItems()
        target = getattr(items[0], "model_target", None) if items else None
        self._session.set_selection(target)

    def _refresh_for(self, obj: object) -> None:
        if isinstance(obj, Variant) and obj is self.current_variant:
            self.rebuild()
            return
        if isinstance(obj, Zone) and obj.name in self._zone_items:
            self._zone_items[obj.name].refresh()
            self._restyle_zones()
            return
        if self._is_in_current_variant_zone(obj):
            self._restyle_zones()
            return
        for item in self.items():
            if getattr(item, "model_target", None) is obj:
                refresh = getattr(item, "refresh", None)
                if callable(refresh):
                    refresh()
                return

    def _restyle_zones(self) -> None:
        variant = self.current_variant
        if variant is None:
            return
        styles = compute_zone_styles(variant)
        for name, item in self._zone_items.items():
            style = styles.get(name)
            if style is not None:
                item.update_style(style.radius, style.fill)

    def _is_in_current_variant_zone(self, obj: object) -> bool:
        variant = self.current_variant
        if variant is None:
            return False
        for zone in variant.zones:
            for mo in zone.mainObjects:
                if mo is obj:
                    return True
        return False


def _parallel_offsets(connections: list[object]) -> dict[int, float]:
    """Compute a per-edge perpendicular offset for groups of parallel connections.

    Connections in the same unordered (from, to) group share a fanout. Each connection's
    perpendicular vector flips when its from_/to are swapped, so the offset sign must
    flip too — otherwise A→B and B→A would land on opposite sides of the centerline
    instead of fanning out together.
    """
    groups: dict[frozenset[str], list[object]] = {}
    for conn in connections:
        key = frozenset({conn.from_, conn.to})  # type: ignore[attr-defined]
        groups.setdefault(key, []).append(conn)

    offsets: dict[int, float] = {}
    for key, group in groups.items():
        n = len(group)
        if n == 1:
            offsets[id(group[0])] = 0.0
            continue
        canonical = sorted(key)
        canonical_from = canonical[0] if canonical else None
        is_self_loop = len(canonical) < 2
        for i, conn in enumerate(group):
            base = (i - (n - 1) / 2.0) * _PARALLEL_SPACING
            sign = 1.0 if is_self_loop or conn.from_ == canonical_from else -1.0  # type: ignore[attr-defined]
            offsets[id(conn)] = base * sign
    return offsets
