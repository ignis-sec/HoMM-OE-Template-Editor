"""GraphScene — binds the current Variant to draggable ZoneItems and EdgeItems."""

from typing import Final

from PySide6.QtWidgets import QGraphicsScene

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

    def rebuild(self) -> None:
        self.clear()
        self._zone_items.clear()

        template = self._session.template
        if not template or not template.variants:
            return
        variant = template.variants[self._session.current_variant_index]

        positions = compute_layout(variant)

        for zone in variant.zones:
            x, y = positions[zone.name]
            item = ZoneItem(zone)
            item.setPos(x * _LAYOUT_SCALE, y * _LAYOUT_SCALE)
            self.addItem(item)
            self._zone_items[zone.name] = item

        for conn in variant.connections:
            edge = EdgeItem(conn, self._zone_items[conn.from_], self._zone_items[conn.to])
            self.addItem(edge)

    def _forward_selection(self) -> None:
        items = self.selectedItems()
        target = getattr(items[0], "model_target", None) if items else None
        self._session.set_selection(target)

    def _refresh_for(self, obj: object) -> None:
        for item in self.items():
            if getattr(item, "model_target", None) is obj:
                refresh = getattr(item, "refresh", None)
                if callable(refresh):
                    refresh()
                return
