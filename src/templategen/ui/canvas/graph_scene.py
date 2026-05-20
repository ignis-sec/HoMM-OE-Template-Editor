"""GraphScene — binds the current Variant to draggable ZoneItems and EdgeItems."""

from typing import Final

from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QGraphicsScene

from templategen.model.variant import Variant
from templategen.services.session import EditorSession
from templategen.ui.canvas.connection_item import EdgeItem
from templategen.ui.canvas.layout import compute_layout
from templategen.ui.canvas.zone_item import ZoneItem

_SCENE_SIZE: Final[float] = 1200.0
_LAYOUT_SCALE: Final[float] = 500.0


class GraphScene(QGraphicsScene):
    def __init__(self, session: EditorSession) -> None:
        super().__init__()
        self._session = session
        self._zone_items: dict[str, ZoneItem] = {}

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

    def rebuild(self) -> None:
        prior_positions = {
            name: item.pos() for name, item in self._zone_items.items()
        }
        self.clear()
        self._zone_items.clear()

        variant = self.current_variant
        if variant is None:
            return

        positions = compute_layout(variant)

        for zone in variant.zones:
            item = ZoneItem(zone)
            if zone.name in prior_positions:
                item.setPos(prior_positions[zone.name])
            else:
                x, y = positions[zone.name]
                item.setPos(x * _LAYOUT_SCALE, y * _LAYOUT_SCALE)
            self.addItem(item)
            self._zone_items[zone.name] = item

        for conn in variant.connections:
            source = self._zone_items.get(conn.from_)
            target = self._zone_items.get(conn.to)
            if source is None or target is None:
                continue
            edge = EdgeItem(conn, source, target)
            self.addItem(edge)

    def viewport_center_scene_pos(self, fallback: QPointF | None = None) -> QPointF:
        if fallback is not None:
            return fallback
        return QPointF(0.0, 0.0)

    def _forward_selection(self) -> None:
        items = self.selectedItems()
        target = getattr(items[0], "model_target", None) if items else None
        self._session.set_selection(target)

    def _refresh_for(self, obj: object) -> None:
        if isinstance(obj, Variant) and obj is self.current_variant:
            self.rebuild()
            return
        for item in self.items():
            if getattr(item, "model_target", None) is obj:
                refresh = getattr(item, "refresh", None)
                if callable(refresh):
                    refresh()
                return
