"""Interaction controllers for the canvas — connect mode, marquee select, drag-rules."""

from PySide6.QtCore import QObject

from templategen.ui.canvas.graph_scene import GraphScene


class CanvasInteraction(QObject):
    def __init__(self, scene: GraphScene) -> None:
        super().__init__()
        self._scene = scene

    def activate(self) -> None:
        raise NotImplementedError

    def deactivate(self) -> None:
        raise NotImplementedError


class ConnectModeInteraction(CanvasInteraction): ...


class MarqueeSelectInteraction(CanvasInteraction): ...
