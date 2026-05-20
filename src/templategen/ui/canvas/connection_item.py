"""EdgeItem — line between two ZoneItems, styled per connection type."""

from typing import Final

from PySide6.QtCore import QLineF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPainterPathStroker, QPen
from PySide6.QtWidgets import QGraphicsItem, QGraphicsObject, QStyleOptionGraphicsItem, QWidget

from templategen.model.connection import (
    DirectConnection,
    GladiatorArenaConnection,
    PortalConnection,
    ProximityConnection,
)
from templategen.model.enums import ConnectionType
from templategen.ui.canvas.zone_item import ZoneItem

_StyledConnection = DirectConnection | PortalConnection | ProximityConnection | GladiatorArenaConnection

_DEFAULT_PEN: Final[QPen] = QPen(QColor("#bcbcc4"), 1.8)
_PORTAL_PEN: Final[QPen] = QPen(QColor("#c8a0ff"), 1.8, Qt.PenStyle.DashLine)
_PROXIMITY_PEN: Final[QPen] = QPen(QColor("#5b6068"), 1.0, Qt.PenStyle.DotLine)
_ARENA_PEN: Final[QPen] = QPen(QColor("#e07070"), 3.0)

_HIT_TOLERANCE: Final[float] = 8.0


def _pen_for(connection: _StyledConnection) -> QPen:
    match connection.connectionType:
        case ConnectionType.PORTAL:
            return _PORTAL_PEN
        case ConnectionType.PROXIMITY:
            return _PROXIMITY_PEN
        case ConnectionType.GLADIATOR_ARENA:
            return _ARENA_PEN
        case _:
            return _DEFAULT_PEN


class EdgeItem(QGraphicsObject):
    def __init__(self, connection: _StyledConnection, source: ZoneItem, target: ZoneItem) -> None:
        super().__init__()
        self._connection = connection
        self._source = source
        self._target = target
        self._pen = _pen_for(connection)
        self.setZValue(-1)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setToolTip(connection.name or f"{connection.from_} → {connection.to}")
        source.add_edge(self)
        target.add_edge(self)

    @property
    def model_target(self) -> _StyledConnection:
        return self._connection

    def refresh(self) -> None:
        self.setToolTip(self._connection.name or f"{self._connection.from_} → {self._connection.to}")
        self.update()

    def update_endpoints(self) -> None:
        self.prepareGeometryChange()
        self.update()

    def _line(self) -> QLineF:
        return QLineF(self._source.center(), self._target.center())

    def boundingRect(self) -> QRectF:
        line = self._line()
        margin = _HIT_TOLERANCE
        return QRectF(line.p1(), line.p2()).normalized().adjusted(-margin, -margin, margin, margin)

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
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(self._pen)
        if self.isSelected():
            pen.setColor(QColor("#fff"))
            pen.setWidthF(pen.widthF() + 1.0)
        painter.setPen(pen)
        painter.drawLine(self._line())
