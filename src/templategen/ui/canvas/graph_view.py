"""GraphView — host for GraphScene with wheel zoom centered on the cursor."""

from typing import Final

from PySide6.QtGui import QPainter, QWheelEvent
from PySide6.QtWidgets import QGraphicsView

from templategen.ui.canvas.graph_scene import GraphScene

_ZOOM_STEP: Final[float] = 1.15


class GraphView(QGraphicsView):
    def __init__(self, scene: GraphScene) -> None:
        super().__init__(scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)

    def wheelEvent(self, event: QWheelEvent) -> None:
        factor = _ZOOM_STEP if event.angleDelta().y() > 0 else 1.0 / _ZOOM_STEP
        self.scale(factor, factor)
