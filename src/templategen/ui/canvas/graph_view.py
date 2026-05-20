"""GraphView — wheel-zoom + connect-mode + Delete-key structural editing."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent, QMouseEvent, QPainter, QWheelEvent
from PySide6.QtWidgets import QGraphicsView

from templategen.model.connection import DirectConnection
from templategen.services.commands import (
    AddConnectionCommand,
    RemoveConnectionCommand,
    RemoveZoneCommand,
)
from templategen.services.naming import unique_connection_name
from templategen.ui.canvas.connection_item import EdgeItem
from templategen.ui.canvas.zone_item import ZoneItem

if TYPE_CHECKING:
    from templategen.model.zone import Zone
    from templategen.ui.canvas.graph_scene import GraphScene

_ZOOM_STEP: Final[float] = 1.15


class GraphView(QGraphicsView):
    connect_mode_changed = Signal(bool)

    def __init__(self, scene: GraphScene) -> None:
        super().__init__(scene)
        self._scene = scene
        self._connect_mode = False
        self._pending_source: ZoneItem | None = None

        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    @property
    def connect_mode(self) -> bool:
        return self._connect_mode

    def set_connect_mode(self, enabled: bool) -> None:
        if enabled == self._connect_mode:
            return
        self._connect_mode = enabled
        self._pending_source = None
        if enabled:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.viewport().setCursor(Qt.CursorShape.CrossCursor)
            selected = self._selected_zone()
            if selected is not None:
                self._pending_source = selected
        else:
            self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
            self.viewport().unsetCursor()
        self.connect_mode_changed.emit(enabled)

    def delete_selected(self) -> None:
        items = self._scene.selectedItems()
        if not items:
            return
        zones: list[ZoneItem] = [i for i in items if isinstance(i, ZoneItem)]
        edges: list[EdgeItem] = [i for i in items if isinstance(i, EdgeItem)]
        if not zones and not edges:
            return

        session = self._scene.session
        variant = self._scene.current_variant
        if variant is None:
            return

        zone_names = {z.model_target.name for z in zones}
        cascade_edges: set[EdgeItem] = set()
        if zones:
            cascade_edges = {
                edge for edge in self._all_edges()
                if edge.model_target.from_ in zone_names or edge.model_target.to in zone_names
            }
        edges_to_remove = {*edges, *cascade_edges}

        label = self._delete_label(zones, edges)
        session.begin_macro(label)
        try:
            for edge in edges_to_remove:
                session.execute(
                    RemoveConnectionCommand(session, variant, edge.model_target)
                )
            for zone_item in zones:
                session.execute(
                    RemoveZoneCommand(session, variant, zone_item.model_target)
                )
        finally:
            session.end_macro()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape and self._connect_mode:
            self.set_connect_mode(False)
            event.accept()
            return
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.delete_selected()
            event.accept()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self._connect_mode and event.button() == Qt.MouseButton.LeftButton:
            self._handle_connect_click(event)
            event.accept()
            return
        super().mousePressEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        factor = _ZOOM_STEP if event.angleDelta().y() > 0 else 1.0 / _ZOOM_STEP
        self.scale(factor, factor)

    def _handle_connect_click(self, event: QMouseEvent) -> None:
        target_item = self._zone_at_viewport_pos(event.position().toPoint())
        if target_item is None:
            self.set_connect_mode(False)
            return
        if self._pending_source is None:
            self._pending_source = target_item
            self._scene.clearSelection()
            target_item.setSelected(True)
            return
        if target_item is self._pending_source:
            return
        self._create_connection(self._pending_source.model_target, target_item.model_target)
        self.set_connect_mode(False)

    def _create_connection(self, source: Zone, target: Zone) -> None:
        variant = self._scene.current_variant
        if variant is None:
            return
        for existing in variant.connections:
            if existing.from_ == source.name and existing.to == target.name:
                return
        session = self._scene.session
        name = unique_connection_name(variant, source.name, target.name)
        connection = DirectConnection(name=name, from_=source.name, to=target.name)
        session.execute(AddConnectionCommand(session, variant, connection))

    def _zone_at_viewport_pos(self, pos: object) -> ZoneItem | None:
        item = self.itemAt(pos)
        while item is not None:
            if isinstance(item, ZoneItem):
                return item
            item = item.parentItem()
        return None

    def _selected_zone(self) -> ZoneItem | None:
        for item in self._scene.selectedItems():
            if isinstance(item, ZoneItem):
                return item
        return None

    def _all_edges(self) -> list[EdgeItem]:
        return [i for i in self._scene.items() if isinstance(i, EdgeItem)]

    def _delete_label(self, zones: list[ZoneItem], edges: list[EdgeItem]) -> str:
        if zones and not edges:
            return "Remove zone" if len(zones) == 1 else f"Remove {len(zones)} zones"
        if edges and not zones:
            return "Remove connection" if len(edges) == 1 else f"Remove {len(edges)} connections"
        return "Remove zones and connections"
