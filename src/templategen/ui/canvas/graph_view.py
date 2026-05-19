"""GraphView — pan, zoom, marquee-select host for the GraphScene."""

from PySide6.QtWidgets import QGraphicsView

from templategen.ui.canvas.graph_scene import GraphScene


class GraphView(QGraphicsView):
    def __init__(self, scene: GraphScene) -> None:
        super().__init__(scene)
