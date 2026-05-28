"""ZoneItem — draggable graphics node representing one Zone."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Final

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsObject,
    QGraphicsSceneMouseEvent,
    QStyleOptionGraphicsItem,
    QWidget,
)

if TYPE_CHECKING:
    from templategen.model.zone import Zone
    from templategen.ui.canvas.connection_item import EdgeItem


DEFAULT_RADIUS: Final[float] = 32.0


class ZoneItem(QGraphicsObject):
    def __init__(self, zone: Zone, *, radius: float = DEFAULT_RADIUS, fill: QColor | None = None) -> None:
        super().__init__()
        self._zone = zone
        self._edges: list[EdgeItem] = []
        self._radius = radius
        self._fill = fill if fill is not None else QColor("#666b75")
        self._drag_start: dict[str, QPointF] = {}
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setToolTip(zone.name)

    @property
    def model_target(self) -> Zone:
        return self._zone

    @property
    def radius(self) -> float:
        return self._radius

    def refresh(self) -> None:
        self.setToolTip(self._zone.name)
        self.update()

    def update_style(self, radius: float, fill: QColor) -> None:
        if radius == self._radius and fill == self._fill:
            return
        if radius != self._radius:
            self.prepareGeometryChange()
            self._radius = radius
        self._fill = fill
        self.update()
        for edge in self._edges:
            edge.update_endpoints()

    def add_edge(self, edge: EdgeItem) -> None:
        self._edges.append(edge)

    def center(self) -> QPointF:
        return self.scenePos()

    def boundingRect(self) -> QRectF:
        r = self._radius
        return QRectF(-r, -r, 2 * r, 2 * r)

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        border = QColor("#fff") if self.isSelected() else self._fill.darker(150)
        painter.setBrush(QBrush(self._fill))
        painter.setPen(QPen(border, 2.5 if self.isSelected() else 1.5))
        painter.drawEllipse(self.boundingRect())

        painter.setPen(QColor("#fff"))
        font = QFont()
        font.setPointSize(max(7, int(8 + self._radius / 32 - 1)))
        painter.setFont(font)
        painter.drawText(self.boundingRect(), Qt.AlignmentFlag.AlignCenter, self._zone.name)

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value: Any) -> Any:
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for edge in self._edges:
                edge.update_endpoints()
        return super().itemChange(change, value)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            scene = self.scene()
            if scene is not None:
                # Capture starting positions for every zone that Qt will drag along with us
                # (selected items move as a group). The clicked zone is always included even
                # if it wasn't part of the selection — Qt selects-on-press in that case.
                companions = [i for i in scene.selectedItems() if isinstance(i, ZoneItem)]
                if self not in companions:
                    companions = [self, *companions]
                self._drag_start = {i._zone.name: QPointF(i.pos()) for i in companions}
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        super().mouseReleaseEvent(event)
        if event.button() != Qt.MouseButton.LeftButton or not self._drag_start:
            self._drag_start = {}
            return
        starts = self._drag_start
        self._drag_start = {}
        scene = self.scene()
        if scene is None or not hasattr(scene, "session") or not hasattr(scene, "zone_items"):
            return
        items = scene.zone_items
        moved: list[tuple[str, QPointF, QPointF]] = []
        for name, start_pos in starts.items():
            item = items.get(name)
            if item is None:
                continue
            end_pos = item.pos()
            if end_pos != start_pos:
                moved.append((name, start_pos, end_pos))
        if not moved:
            return

        from templategen.services.commands import MoveZoneCommand

        session = scene.session
        if len(moved) == 1:
            name, start, end = moved[0]
            session.execute(MoveZoneCommand(session, scene, name, start, end))
            return
        session.begin_macro(f"Move {len(moved)} zones")
        try:
            for name, start, end in moved:
                session.execute(MoveZoneCommand(session, scene, name, start, end))
        finally:
            session.end_macro()
