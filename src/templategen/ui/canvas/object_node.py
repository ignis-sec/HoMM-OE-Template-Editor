"""ObjectNode + ConnectionNode + RoadEdgeItem — graphics items for the road-graph view.

In road-graph mode the scene drops zone circles and connection lines, and instead shows:
- One ObjectNode per MainObject in each zone (city / spawn / outpost / arena / empty),
  rendered with a thumbnail (faction icon for cities, player colour for spawns, a type
  glyph for the rest);
- One ConnectionNode per inter-zone connection, sitting at the midpoint between the
  two zones it connects, so roads that lead to a connection have an explicit endpoint
  to terminate at;
- One RoadEdgeItem per Road, drawn between the resolved endpoint nodes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Final

from PySide6.QtCore import QLineF, QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPainterPathStroker,
    QPen,
)
from PySide6.QtWidgets import QGraphicsItem, QGraphicsObject

from templategen.model.enums import RoadType

if TYPE_CHECKING:
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QStyleOptionGraphicsItem, QWidget


_OBJECT_RADIUS: Final[float] = 18.0
_CONNECTION_HALF: Final[float] = 8.0
_HIT_TOLERANCE: Final[float] = 6.0
_ROAD_PENS: Final[dict[RoadType, QPen]] = {
    RoadType.STONE: QPen(QColor("#c4c8d0"), 2.4),  # cool stone-grey
    RoadType.DIRT: QPen(QColor("#a06840"), 2.4),   # warm earthy brown
}
_UNKNOWN_ROAD_PEN: Final[QPen] = QPen(QColor("#e8a040"), 2.4)


def _pen_for_road(road: object) -> QPen:
    return _ROAD_PENS.get(getattr(road, "type", None), _UNKNOWN_ROAD_PEN)


class ObjectNode(QGraphicsObject):
    def __init__(
        self,
        model: object,
        label: str,
        *,
        icon: QIcon | None = None,
        fill: QColor,
        glyph: str | None = None,
        owning_zone_name: str | None = None,
    ) -> None:
        super().__init__()
        self._model = model
        self._label = label
        self._fill = fill
        self._glyph = glyph
        self._owning_zone_name = owning_zone_name
        size = int(_OBJECT_RADIUS * 2)
        self._pixmap = icon.pixmap(size, size) if icon is not None else None
        self._edges: list[Any] = []
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setZValue(3)
        self.setToolTip(label)

    @property
    def model_target(self) -> object:
        return self._model

    @property
    def owning_zone_name(self) -> str | None:
        """The zone this node was placed under in the road graph. Disambiguates
        which zone to route through when the underlying model object (e.g. a
        bundle ContentItem) is reachable from several zones."""
        return self._owning_zone_name

    def add_edge(self, edge: object) -> None:
        self._edges.append(edge)

    def refresh(self) -> None:
        self.update()

    def boundingRect(self) -> QRectF:
        r = _OBJECT_RADIUS + 2
        return QRectF(-r, -r, 2 * r, 2 * r)

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        ring = QRectF(-_OBJECT_RADIUS, -_OBJECT_RADIUS, 2 * _OBJECT_RADIUS, 2 * _OBJECT_RADIUS)
        border_color = QColor("#fff") if self.isSelected() else QColor("#1a1a1d")
        painter.setBrush(QBrush(self._fill))
        painter.setPen(QPen(border_color, 2.0 if self.isSelected() else 1.4))
        painter.drawEllipse(ring)
        if self._pixmap is not None:
            inset = ring.adjusted(3, 3, -3, -3)
            painter.drawPixmap(inset.toRect(), self._pixmap)
        elif self._glyph:
            painter.setPen(QColor("#fff"))
            font = QFont()
            font.setBold(True)
            font.setPointSize(11)
            painter.setFont(font)
            painter.drawText(ring, Qt.AlignmentFlag.AlignCenter, self._glyph)

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value: Any) -> Any:
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for edge in self._edges:
                edge.update_endpoints()
        return super().itemChange(change, value)


class ConnectionNode(QGraphicsObject):
    def __init__(self, connection: object, label: str) -> None:
        super().__init__()
        self._connection = connection
        self._label = label
        self._edges: list[Any] = []
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setZValue(3)
        self.setToolTip(label)

    @property
    def model_target(self) -> object:
        return self._connection

    def add_edge(self, edge: object) -> None:
        self._edges.append(edge)

    def refresh(self) -> None:
        self.update()

    def boundingRect(self) -> QRectF:
        m = _CONNECTION_HALF + 2
        return QRectF(-m, -m, 2 * m, 2 * m)

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        s = _CONNECTION_HALF
        points = [QPointF(0, -s), QPointF(s, 0), QPointF(0, s), QPointF(-s, 0)]
        border_color = QColor("#fff") if self.isSelected() else QColor("#1a1a1d")
        painter.setBrush(QBrush(QColor("#9ea3b0")))
        painter.setPen(QPen(border_color, 1.5))
        painter.drawPolygon(points)

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value: Any) -> Any:
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for edge in self._edges:
                edge.update_endpoints()
        return super().itemChange(change, value)


class RoadEdgeItem(QGraphicsObject):
    def __init__(
        self,
        road: object,
        source: QGraphicsObject,
        target: QGraphicsObject,
        tooltip: str,
    ) -> None:
        super().__init__()
        self._road = road
        self._source = source
        self._target = target
        self.setZValue(1)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setToolTip(tooltip)
        source.add_edge(self)  # type: ignore[attr-defined]
        target.add_edge(self)  # type: ignore[attr-defined]

    @property
    def model_target(self) -> object:
        return self._road

    def refresh(self) -> None:
        self.update()

    def update_endpoints(self) -> None:
        self.prepareGeometryChange()
        self.update()

    def _line(self) -> QLineF:
        return QLineF(self._source.scenePos(), self._target.scenePos())

    def boundingRect(self) -> QRectF:
        line = self._line()
        m = _HIT_TOLERANCE
        return QRectF(line.p1(), line.p2()).normalized().adjusted(-m, -m, m, m)

    def shape(self) -> QPainterPath:
        path = QPainterPath()
        line = self._line()
        path.moveTo(line.p1())
        path.lineTo(line.p2())
        stroker = QPainterPathStroker()
        stroker.setWidth(_HIT_TOLERANCE)
        return stroker.createStroke(path)

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        line = self._line()
        if line.length() < 1.0:
            return
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(_pen_for_road(self._road))
        if self.isSelected():
            pen.setColor(QColor("#fff"))
            pen.setWidthF(pen.widthF() + 1.0)
        painter.setPen(pen)
        painter.drawLine(line)
