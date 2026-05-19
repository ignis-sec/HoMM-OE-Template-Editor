"""Inspector — contextual editor for the currently selected entity."""

from PySide6.QtWidgets import QWidget

from templategen.services.session import EditorSession


class Inspector(QWidget):
    def __init__(self, session: EditorSession) -> None:
        super().__init__()
        self._session = session
        self.setMinimumWidth(300)

    def set_target(self, target: object | None) -> None:
        raise NotImplementedError
