"""ZoneItem — draggable graphics node representing one Zone."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Final

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QGraphicsItem, QGraphicsObject, QStyleOptionGraphicsItem, QWidget

from templategen.model.enums import PlayerId
from templategen.model.main_objects import (
    AbandonedOutpostObject,
    CityObject,
    GladiatorArenaObject,
    SpawnObject,
)

if TYPE_CHECKING:
    from templategen.model.zone import Zone
    from templategen.ui.canvas.connection_item import EdgeItem

_PLAYER_COLOR: Final[dict[str, QColor]] = {
    PlayerId.PLAYER_1: QColor("#d04b4b"),
    PlayerId.PLAYER_2: QColor("#3a78d6"),
    PlayerId.PLAYER_3: QColor("#5ab84b"),
    PlayerId.PLAYER_4: QColor("#e7b93a"),
    PlayerId.PLAYER_5: QColor("#3fb8b8"),
    PlayerId.PLAYER_6: QColor("#a358cf"),
    PlayerId.PLAYER_7: QColor("#e8703a"),
    PlayerId.PLAYER_8: QColor("#e58fc1"),
}
_CITY_COLOR: Final[QColor] = QColor("#a8845a")
_TREASURE_COLOR: Final[QColor] = QColor("#b04848")
_CONNECTOR_COLOR: Final[QColor] = QColor("#666b75")

_RADIUS: Final[float] = 32.0


def _fill_color(zone: Zone) -> QColor:
    for mo in zone.mainObjects:
        if isinstance(mo, SpawnObject) and mo.spawn is not None:
            return _PLAYER_COLOR.get(mo.spawn, _TREASURE_COLOR)
        if isinstance(mo, CityObject):
            return _CITY_COLOR
        if isinstance(mo, AbandonedOutpostObject | GladiatorArenaObject):
            return _TREASURE_COLOR
    return _CONNECTOR_COLOR


class ZoneItem(QGraphicsObject):
    def __init__(self, zone: Zone) -> None:
        super().__init__()
        self._zone = zone
        self._edges: list[EdgeItem] = []
        self._fill = _fill_color(zone)
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
        return QRectF(-_RADIUS, -_RADIUS, 2 * _RADIUS, 2 * _RADIUS)

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
        font.setPointSize(8)
        painter.setFont(font)
        painter.drawText(self.boundingRect(), Qt.AlignmentFlag.AlignCenter, self._zone.name)

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value: Any) -> Any:
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for edge in self._edges:
                edge.update_endpoints()
        return super().itemChange(change, value)
