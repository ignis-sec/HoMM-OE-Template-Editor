"""VariantTabBar — switch between the template's variants."""

from PySide6.QtWidgets import QTabBar

from templategen.services.session import EditorSession


class VariantTabBar(QTabBar):
    def __init__(self, session: EditorSession) -> None:
        super().__init__()
        self._session = session
