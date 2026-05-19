"""Inspector — read-only contextual view of the current selection."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFormLayout, QFrame, QLabel, QScrollArea, QVBoxLayout, QWidget

from templategen.model.connection import _ConnectionBase
from templategen.model.zone import Zone
from templategen.services.session import EditorSession


def _label(text: str) -> QLabel:
    label = QLabel(text)
    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    label.setWordWrap(True)
    return label


class Inspector(QWidget):
    def __init__(self, session: EditorSession) -> None:
        super().__init__()
        self._session = session
        self.setMinimumWidth(300)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        self._inner = QWidget()
        scroll.setWidget(self._inner)
        self._form = QFormLayout(self._inner)
        self._form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        session.selection_changed.connect(self.set_target)
        session.template_changed.connect(lambda: self.set_target(None))

        self.set_target(None)

    def set_target(self, target: object | None) -> None:
        while self._form.rowCount() > 0:
            self._form.removeRow(0)

        if target is None:
            self._form.addRow(_label("Select a zone or connection on the canvas."))
            return

        if isinstance(target, Zone):
            self._populate_zone(target)
        elif isinstance(target, _ConnectionBase):
            self._populate_connection(target)
        else:
            self._form.addRow("Type:", _label(type(target).__name__))

    def _populate_zone(self, zone: Zone) -> None:
        self._form.addRow("Kind:", _label("Zone"))
        self._form.addRow("Name:", _label(zone.name))
        self._form.addRow("Size:", _label(str(zone.size)))
        self._form.addRow("Layout:", _label(zone.layout))
        if zone.mainObjects:
            kinds = ", ".join(getattr(mo, "type", "Empty") for mo in zone.mainObjects)
            self._form.addRow("Main objects:", _label(kinds))
        if zone.mandatoryContent:
            self._form.addRow("Mandatory:", _label(", ".join(zone.mandatoryContent)))
        if zone.guardedContentValue is not None:
            self._form.addRow("Guarded value:", _label(str(zone.guardedContentValue)))

    def _populate_connection(self, conn: _ConnectionBase) -> None:
        self._form.addRow("Kind:", _label(f"Connection ({conn.connectionType.value})"))
        if conn.name:
            self._form.addRow("Name:", _label(conn.name))
        self._form.addRow("From:", _label(conn.from_))
        self._form.addRow("To:", _label(conn.to))
        if conn.guardValue is not None:
            self._form.addRow("Guard value:", _label(str(conn.guardValue)))
        if conn.road is not None:
            self._form.addRow("Road:", _label("yes" if conn.road else "no"))
