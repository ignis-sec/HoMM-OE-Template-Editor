"""ZoneItem — draggable graphics node representing one Zone."""

from PySide6.QtCore import QRectF
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QGraphicsObject, QStyleOptionGraphicsItem, QWidget

from templategen.model.zone import Zone


class ZoneItem(QGraphicsObject):
    def __init__(self, zone: Zone) -> None:
        super().__init__()
        self._zone = zone

    def boundingRect(self) -> QRectF:
        raise NotImplementedError

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        raise NotImplementedError
