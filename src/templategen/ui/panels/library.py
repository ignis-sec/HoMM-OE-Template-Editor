"""LibraryPanel — browse and edit zoneLayouts, mandatoryContent, contentCountLimits."""

from PySide6.QtWidgets import QWidget

from templategen.services.session import EditorSession


class LibraryPanel(QWidget):
    def __init__(self, session: EditorSession) -> None:
        super().__init__()
        self._session = session
        self.setMinimumWidth(240)
