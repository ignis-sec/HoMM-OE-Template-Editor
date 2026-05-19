"""GraphScene — binds the current Variant's zones and connections to graphics items."""

from PySide6.QtWidgets import QGraphicsScene

from templategen.services.session import EditorSession


class GraphScene(QGraphicsScene):
    def __init__(self, session: EditorSession) -> None:
        super().__init__()
        self._session = session

    def rebuild(self) -> None:
        raise NotImplementedError
