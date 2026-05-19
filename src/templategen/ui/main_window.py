"""Main application window — wires canvas, panels, menus, and toolbar."""

from PySide6.QtWidgets import QMainWindow

from templategen.services.session import EditorSession


class MainWindow(QMainWindow):
    def __init__(self, session: EditorSession) -> None:
        super().__init__()
        self._session = session

    def _build_menus(self) -> None:
        raise NotImplementedError

    def _build_toolbar(self) -> None:
        raise NotImplementedError

    def _build_docks(self) -> None:
        raise NotImplementedError
