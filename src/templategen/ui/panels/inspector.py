"""Inspector — contextual editor for the current selection."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QLabel,
    QLineEdit,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from templategen.model.connection import _ConnectionBase
from templategen.model.zone import Zone
from templategen.ui.widgets.field_binding import (
    bind_bool,
    bind_choice,
    bind_float,
    bind_int,
    bind_string,
)

if TYPE_CHECKING:
    from templategen.services.session import EditorSession
    from templategen.ui.widgets.field_binding import Refresh


def _readonly(text: str) -> QLabel:
    label = QLabel(text)
    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    label.setWordWrap(True)
    return label


class Inspector(QWidget):
    def __init__(self, session: EditorSession) -> None:
        super().__init__()
        self._session = session
        self._target: object | None = None
        self._refreshers: list[Refresh] = []

        self.setMinimumWidth(320)

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
        session.model_object_changed.connect(self._on_model_changed)

        self.set_target(None)

    def set_target(self, target: object | None) -> None:
        self._refreshers.clear()
        self._clear_form()

        self._target = target

        if target is None:
            self._form.addRow(_readonly("Select a zone or connection on the canvas."))
            return

        if isinstance(target, Zone):
            self._populate_zone(target)
        elif isinstance(target, _ConnectionBase):
            self._populate_connection(target)
        else:
            self._form.addRow("Type:", _readonly(type(target).__name__))

    def _clear_form(self) -> None:
        while self._form.rowCount() > 0:
            self._form.removeRow(0)

    def _on_model_changed(self, obj: object) -> None:
        if obj is self._target:
            for refresh in self._refreshers:
                refresh()

    def _populate_zone(self, zone: Zone) -> None:
        self._form.addRow("Kind:", _readonly("Zone"))

        name_edit = QLineEdit()
        self._refreshers.append(bind_string(name_edit, zone, "name", self._session))
        self._form.addRow("Name:", name_edit)

        size_edit = QDoubleSpinBox()
        size_edit.setRange(0.01, 10.0)
        size_edit.setSingleStep(0.05)
        size_edit.setDecimals(2)
        self._refreshers.append(bind_float(size_edit, zone, "size", self._session))
        self._form.addRow("Size:", size_edit)

        layout_combo = QComboBox()
        layouts = self._available_layouts()
        self._refreshers.append(bind_choice(layout_combo, zone, "layout", self._session, layouts))
        self._form.addRow("Layout:", layout_combo)

        guarded_edit = QSpinBox()
        guarded_edit.setRange(0, 100_000_000)
        guarded_edit.setSingleStep(1000)
        self._refreshers.append(bind_int(guarded_edit, zone, "guardedContentValue", self._session))
        self._form.addRow("Guarded value:", guarded_edit)

        unguarded_edit = QSpinBox()
        unguarded_edit.setRange(0, 100_000_000)
        unguarded_edit.setSingleStep(1000)
        self._refreshers.append(bind_int(unguarded_edit, zone, "unguardedContentValue", self._session))
        self._form.addRow("Unguarded value:", unguarded_edit)

        resources_edit = QSpinBox()
        resources_edit.setRange(0, 100_000_000)
        resources_edit.setSingleStep(1000)
        self._refreshers.append(bind_int(resources_edit, zone, "resourcesValue", self._session))
        self._form.addRow("Resources value:", resources_edit)

        if zone.mainObjects:
            kinds = ", ".join(getattr(mo, "type", "Empty") for mo in zone.mainObjects)
            self._form.addRow("Main objects:", _readonly(kinds))
        if zone.mandatoryContent:
            self._form.addRow("Mandatory:", _readonly(", ".join(zone.mandatoryContent)))

    def _populate_connection(self, conn: _ConnectionBase) -> None:
        self._form.addRow("Kind:", _readonly(f"Connection ({conn.connectionType.value})"))

        name_edit = QLineEdit()
        self._refreshers.append(bind_string(name_edit, conn, "name", self._session, optional=True))
        self._form.addRow("Name:", name_edit)

        self._form.addRow("From:", _readonly(conn.from_))
        self._form.addRow("To:", _readonly(conn.to))

        guard_edit = QSpinBox()
        guard_edit.setRange(0, 100_000_000)
        guard_edit.setSingleStep(1000)
        self._refreshers.append(bind_int(guard_edit, conn, "guardValue", self._session))
        self._form.addRow("Guard value:", guard_edit)

        road_edit = QCheckBox()
        self._refreshers.append(bind_bool(road_edit, conn, "road", self._session))
        self._form.addRow("Road:", road_edit)

    def _available_layouts(self) -> list[str]:
        template = self._session.template
        if template is None:
            return []
        return [zl.name for zl in template.zoneLayouts]
