"""EdgeItem — graphics edge representing one Connection between two zones."""

from PySide6.QtCore import QRectF
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QGraphicsObject, QStyleOptionGraphicsItem, QWidget

from templategen.model.connection import Connection
from templategen.ui.canvas.zone_item import ZoneItem


class EdgeItem(QGraphicsObject):
    def __init__(self, connection: Connection, source: ZoneItem, target: ZoneItem) -> None:
        super().__init__()
        self._connection = connection
        self._source = source
        self._target = target

    def boundingRect(self) -> QRectF:
        raise NotImplementedError

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        raise NotImplementedError
