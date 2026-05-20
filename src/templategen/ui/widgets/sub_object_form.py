"""LazySubObjectGroup — collapsible group for editing an optional embedded sub-object."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from templategen.services.commands import EditFieldCommand

if TYPE_CHECKING:
    from collections.abc import Callable

    from templategen.services.session import EditorSession
    from templategen.ui.widgets.field_binding import Refresh

PopulateFn = "Callable[[QFormLayout, Any, list[Refresh]], None]"


class LazySubObjectGroup(QGroupBox):
    def __init__(
        self,
        title: str,
        parent_target: object,
        field: str,
        factory: Callable[[], Any],
        populate: Callable[[QFormLayout, Any, list[Refresh]], None],
        session: EditorSession,
    ) -> None:
        super().__init__(title)
        self._parent = parent_target
        self._field = field
        self._factory = factory
        self._populate = populate
        self._session = session
        self._sub_refreshers: list[Refresh] = []
        self._current_sub: Any = None

        self._outer = QVBoxLayout(self)
        self._build()
        session.model_object_changed.connect(self._on_model_changed)

    def _on_model_changed(self, obj: object) -> None:
        if obj is self._parent:
            new_sub = getattr(self._parent, self._field)
            if new_sub is not self._current_sub:
                self._build()
            return
        if obj is self._current_sub:
            for refresh in self._sub_refreshers:
                refresh()

    def _build(self) -> None:
        while self._outer.count():
            item = self._outer.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.deleteLater()
        self._sub_refreshers.clear()

        current = getattr(self._parent, self._field)
        self._current_sub = current

        if current is None:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            hint = QLabel("(not set)")
            hint.setStyleSheet("color: #888;")
            row_layout.addWidget(hint)
            row_layout.addStretch()
            enable = QPushButton("Enable")
            enable.clicked.connect(self._enable)
            row_layout.addWidget(enable, alignment=Qt.AlignmentFlag.AlignRight)
            self._outer.addWidget(row)
            return

        inner = QWidget()
        form = QFormLayout(inner)
        form.setContentsMargins(0, 0, 0, 0)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self._populate(form, current, self._sub_refreshers)

        clear_row = QWidget()
        clear_layout = QHBoxLayout(clear_row)
        clear_layout.setContentsMargins(0, 0, 0, 0)
        clear_layout.addStretch()
        clear = QPushButton("Clear")
        clear.clicked.connect(self._clear)
        clear_layout.addWidget(clear)

        self._outer.addWidget(inner)
        self._outer.addWidget(clear_row)

    def _enable(self) -> None:
        self._session.execute(
            EditFieldCommand(self._session, self._parent, self._field, self._factory())
        )

    def _clear(self) -> None:
        self._session.execute(EditFieldCommand(self._session, self._parent, self._field, None))
