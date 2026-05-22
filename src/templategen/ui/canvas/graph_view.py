"""GraphView — wheel-zoom + click-to-place + connect-mode + Delete-key structural editing."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QAction, QContextMenuEvent, QKeyEvent, QMouseEvent, QPainter, QWheelEvent
from PySide6.QtWidgets import QGraphicsView, QMenu

from templategen.model.connection import DirectConnection
from templategen.model.zone import Zone
from templategen.services.commands import (
    AddConnectionCommand,
    AddZoneCommand,
    RemoveConnectionCommand,
    RemoveZoneCommand,
)
from templategen.services.naming import unique_connection_name, unique_zone_name
from templategen.ui.canvas.alignment import (
    align_circle,
    align_horizontal,
    align_line,
    align_vertical,
    distribute_along_line,
    distribute_x,
    distribute_y,
)
from templategen.ui.canvas.connection_item import EdgeItem
from templategen.ui.canvas.zone_item import ZoneItem

if TYPE_CHECKING:
    from templategen.ui.canvas.graph_scene import GraphScene

_ZOOM_STEP: Final[float] = 1.15
_DEFAULT_ZONE_SIZE: Final[float] = 5.0


class GraphView(QGraphicsView):
    connect_mode_changed = Signal(bool)
    place_mode_changed = Signal(bool)

    def __init__(self, scene: GraphScene) -> None:
        super().__init__(scene)
        self._scene = scene
        self._connect_mode = False
        self._place_mode = False
        self._pending_source: ZoneItem | None = None

        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    @property
    def connect_mode(self) -> bool:
        return self._connect_mode

    @property
    def place_mode(self) -> bool:
        return self._place_mode

    def set_connect_mode(self, enabled: bool) -> None:
        if enabled == self._connect_mode:
            return
        if enabled:
            self.set_place_mode(False)
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

    def set_place_mode(self, enabled: bool) -> None:
        if enabled == self._place_mode:
            return
        if enabled:
            self.set_connect_mode(False)
            if self._scene.current_variant is None:
                self.place_mode_changed.emit(False)
                return
        self._place_mode = enabled
        if enabled:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.viewport().setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
            self.viewport().unsetCursor()
        self.place_mode_changed.emit(enabled)

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

        # Resolve everything to model objects up front. We never reuse the Qt items
        # after the macro starts because mid-iteration scene rebuilds destroy them.
        zones_to_remove = [z.model_target for z in zones]
        zone_names = {z.name for z in zones_to_remove}
        explicit_connections = [e.model_target for e in edges]
        explicit_ids = {id(c) for c in explicit_connections}

        cascade_connections = [
            c for c in variant.connections
            if id(c) not in explicit_ids and (c.from_ in zone_names or c.to in zone_names)
        ]
        connections_to_remove = explicit_connections + cascade_connections

        label = self._delete_label(zones, edges)
        session.begin_macro(label)
        try:
            for connection in connections_to_remove:
                session.execute(RemoveConnectionCommand(session, variant, connection))
            for zone in zones_to_remove:
                session.execute(RemoveZoneCommand(session, variant, zone))
        finally:
            session.end_macro()

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        if self._connect_mode or self._place_mode:
            super().contextMenuEvent(event)
            return
        selected_zones = [i for i in self._scene.selectedItems() if isinstance(i, ZoneItem)]
        if len(selected_zones) < 2:
            super().contextMenuEvent(event)
            return

        menu = QMenu(self)
        align_actions = [
            ("Align Horizontally", align_horizontal, 2),
            ("Align Vertically", align_vertical, 2),
            ("Align in a Line", align_line, 2),
            ("Align in a Circle", align_circle, 3),
        ]
        distribute_actions = [
            ("Set Equal Distance", distribute_along_line, 2),
            ("Set Equal Distance (X)", distribute_x, 2),
            ("Set Equal Distance (Y)", distribute_y, 2),
        ]
        for group in (align_actions, distribute_actions):
            for label, op, min_zones in group:
                action = QAction(label, menu)
                action.setEnabled(len(selected_zones) >= min_zones)
                action.triggered.connect(
                    lambda _checked=False, zs=selected_zones, fn=op: self._apply_alignment(zs, fn)
                )
                menu.addAction(action)
            if group is align_actions:
                menu.addSeparator()

        menu.exec(event.globalPos())
        event.accept()

    def _apply_alignment(self, zones: list[ZoneItem], op: object) -> None:
        before = [(z.pos().x(), z.pos().y()) for z in zones]
        after = op(before)
        for zone, (nx, ny) in zip(zones, after, strict=True):
            zone.setPos(nx, ny)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            if self._connect_mode:
                self.set_connect_mode(False)
                event.accept()
                return
            if self._place_mode:
                self.set_place_mode(False)
                event.accept()
                return
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.delete_selected()
            event.accept()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            if self._place_mode:
                self._handle_place_click(event)
                event.accept()
                return
            if self._connect_mode:
                self._handle_connect_click(event)
                event.accept()
                return
        super().mousePressEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        factor = _ZOOM_STEP if event.angleDelta().y() > 0 else 1.0 / _ZOOM_STEP
        self.scale(factor, factor)

    def _handle_place_click(self, event: QMouseEvent) -> None:
        variant = self._scene.current_variant
        if variant is None:
            self.set_place_mode(False)
            return
        scene_pos = self.mapToScene(event.position().toPoint())
        template = self._scene.session.template
        layout = template.zoneLayouts[0].name if template and template.zoneLayouts else ""
        name = unique_zone_name(variant)
        zone = Zone(name=name, size=_DEFAULT_ZONE_SIZE, layout=layout)
        self._scene.stage_position(name, QPointF(scene_pos))
        self._scene.session.execute(AddZoneCommand(self._scene.session, variant, zone))
        self.set_place_mode(False)

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

    def _delete_label(self, zones: list[ZoneItem], edges: list[EdgeItem]) -> str:
        if zones and not edges:
            return "Remove zone" if len(zones) == 1 else f"Remove {len(zones)} zones"
        if edges and not zones:
            return "Remove connection" if len(edges) == 1 else f"Remove {len(edges)} connections"
        return "Remove zones and connections"
