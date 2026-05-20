"""ZoneItem — draggable graphics node representing one Zone."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Final

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QGraphicsItem, QGraphicsObject, QStyleOptionGraphicsItem, QWidget

if TYPE_CHECKING:
    from PySide6.QtCore import QPointF

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
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setToolTip(zone.name)

    @property
    def model_target(self) -> Zone:
        return self._zone

    def refresh(self) -> None:
        self.setToolTip(self._zone.name)
        self.update()

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
