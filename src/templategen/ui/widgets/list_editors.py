"""Editor widgets for list-typed model fields."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QMenu,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from templategen.services.commands import AddListItemCommand, EditFieldCommand, RemoveListItemCommand

if TYPE_CHECKING:
    from collections.abc import Callable

    from templategen.services.session import EditorSession


class _ListEditorBase(QWidget):
    def __init__(
        self,
        target: object,
        field: str,
        session: EditorSession,
        *,
        accept_single_string: bool = False,
    ) -> None:
        super().__init__()
        self._target = target
        self._field = field
        self._session = session
        self._accept_single_string = accept_single_string

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(2)

        self._rows_host = QWidget()
        self._rows = QVBoxLayout(self._rows_host)
        self._rows.setContentsMargins(0, 0, 0, 0)
        self._rows.setSpacing(2)
        outer.addWidget(self._rows_host)

        self._add_button = QPushButton("+ Add")
        self._add_button.clicked.connect(self._on_add)
        outer.addWidget(self._add_button, alignment=outer.alignment())

        self.refresh()

    def refresh(self) -> None:
        while self._rows.count():
            item = self._rows.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.deleteLater()

        current = self._current_as_list()
        for index, value in enumerate(current):
            self._rows.addWidget(self._build_row(index, value))

    def _current_as_list(self) -> list[Any]:
        raw = getattr(self._target, self._field)
        if raw is None:
            return []
        if self._accept_single_string and isinstance(raw, str):
            return [raw]
        return list(raw)

    def _on_add(self) -> None:
        current = self._current_as_list()
        current.append(self._default_value())
        self._commit(current)

    def _remove_row(self, index: int) -> None:
        current = self._current_as_list()
        if 0 <= index < len(current):
            current.pop(index)
            self._commit(current)

    def _on_changed(self, index: int, new_value: Any) -> None:
        current = self._current_as_list()
        if 0 <= index < len(current) and current[index] != new_value:
            current[index] = new_value
            self._commit(current)

    def _commit(self, new_list: list[Any]) -> None:
        old = getattr(self._target, self._field)
        if self._accept_single_string and isinstance(old, str) and len(new_list) == 1:
            new_value: Any = new_list[0]
        elif not new_list and old is None:
            return
        elif not new_list:
            new_value = None
        else:
            new_value = new_list
        if new_value == old:
            return
        self._session.execute(EditFieldCommand(self._session, self._target, self._field, new_value))

    def _build_row(self, index: int, value: Any) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        layout.addWidget(self._build_input(index, value), stretch=1)

        remove = QPushButton("-")
        remove.setMaximumWidth(28)
        remove.setToolTip("Remove this row")
        remove.clicked.connect(lambda _checked=False, i=index: self._remove_row(i))
        layout.addWidget(remove)

        return row

    def _build_input(self, index: int, value: Any) -> QWidget:
        raise NotImplementedError

    def _default_value(self) -> Any:
        raise NotImplementedError


class ScalarListEditor(_ListEditorBase):
    def __init__(
        self,
        target: object,
        field: str,
        session: EditorSession,
        *,
        item_type: type = str,
        accept_single_string: bool = False,
    ) -> None:
        self._item_type = item_type
        super().__init__(target, field, session, accept_single_string=accept_single_string)

    def _default_value(self) -> Any:
        return 0 if self._item_type is int else ""

    def _build_input(self, index: int, value: Any) -> QWidget:
        if self._item_type is int:
            widget = QSpinBox()
            widget.setRange(-1_000_000_000, 1_000_000_000)
            widget.setValue(int(value) if value is not None else 0)
            widget.editingFinished.connect(
                lambda i=index, w=widget: self._on_changed(i, w.value())
            )
            return widget

        widget = QLineEdit()
        widget.setText("" if value is None else str(value))
        widget.editingFinished.connect(
            lambda i=index, w=widget: self._on_changed(i, w.text())
        )
        return widget


class SubObjectListEditor(QWidget):
    def __init__(
        self,
        target: object,
        field: str,
        session: EditorSession,
        *,
        factories: list[tuple[str, Callable[[], Any]]],
        summary: Callable[[Any], str],
        on_drill_in: Callable[[Any], None],
    ) -> None:
        super().__init__()
        self._target = target
        self._field = field
        self._session = session
        self._factories = factories
        self._summary = summary
        self._on_drill_in = on_drill_in

        session.model_object_changed.connect(self._on_model_changed)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(2)

        self._rows_host = QWidget()
        self._rows = QVBoxLayout(self._rows_host)
        self._rows.setContentsMargins(0, 0, 0, 0)
        self._rows.setSpacing(2)
        outer.addWidget(self._rows_host)

        self._add_button = QPushButton("+ Add")
        if len(factories) == 1:
            self._add_button.clicked.connect(lambda: self._add(factories[0][1]))
        else:
            menu = QMenu(self._add_button)
            for label, factory in factories:
                action = menu.addAction(label)
                action.triggered.connect(lambda _checked=False, f=factory: self._add(f))
            self._add_button.setMenu(menu)
        outer.addWidget(self._add_button)

        self.refresh()

    def refresh(self) -> None:
        while self._rows.count():
            item = self._rows.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.deleteLater()

        current = getattr(self._target, self._field) or []
        if not isinstance(current, list):
            return
        for index, sub_obj in enumerate(current):
            self._rows.addWidget(self._build_row(index, sub_obj))

    def _on_model_changed(self, obj: object) -> None:
        if obj is self._target:
            self.refresh()
            return
        current = getattr(self._target, self._field, None)
        if isinstance(current, list) and any(item is obj for item in current):
            self.refresh()

    def _build_row(self, index: int, sub_obj: Any) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        open_button = QPushButton(f"[{index}] {self._summary(sub_obj)}")
        open_button.setStyleSheet("text-align: left; padding-left: 6px;")
        open_button.clicked.connect(lambda _checked=False, obj=sub_obj: self._on_drill_in(obj))
        layout.addWidget(open_button, stretch=1)

        remove = QPushButton("-")
        remove.setMaximumWidth(28)
        remove.setToolTip("Remove")
        remove.clicked.connect(lambda _checked=False, obj=sub_obj: self._remove(obj))
        layout.addWidget(remove)

        return row

    def _add(self, factory: Callable[[], Any]) -> None:
        self._session.execute(
            AddListItemCommand(self._session, self._target, self._field, factory())
        )

    def _remove(self, sub_obj: Any) -> None:
        self._session.execute(
            RemoveListItemCommand(self._session, self._target, self._field, sub_obj)
        )


class InlineSubObjectListEditor(QWidget):
    def __init__(
        self,
        target: object,
        field: str,
        session: EditorSession,
        *,
        factories: list[tuple[str, Callable[[], Any]]],
        populate: Callable[[QFormLayout, Any, list[Any]], None],
        title_for_item: Callable[[Any, int], str],
    ) -> None:
        super().__init__()
        self._target = target
        self._field = field
        self._session = session
        self._factories = factories
        self._populate = populate
        self._title_for = title_for_item
        self._row_refreshers_by_id: dict[int, list[Callable[[], None]]] = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(4)

        self._rows_host = QWidget()
        self._rows = QVBoxLayout(self._rows_host)
        self._rows.setContentsMargins(0, 0, 0, 0)
        self._rows.setSpacing(4)
        outer.addWidget(self._rows_host)

        self._add_button = QPushButton("+ Add")
        if len(factories) == 1:
            self._add_button.clicked.connect(lambda: self._add(factories[0][1]))
        else:
            menu = QMenu(self._add_button)
            for label, factory in factories:
                action = menu.addAction(label)
                action.triggered.connect(lambda _checked=False, f=factory: self._add(f))
            self._add_button.setMenu(menu)
        outer.addWidget(self._add_button, alignment=Qt.AlignmentFlag.AlignLeft)

        session.model_object_changed.connect(self._on_model_changed)
        self.refresh()

    def _on_model_changed(self, obj: object) -> None:
        if obj is self._target:
            self.refresh()
            return
        refreshers = self._row_refreshers_by_id.get(id(obj))
        if refreshers is not None:
            for refresh in refreshers:
                refresh()

    def refresh(self) -> None:
        while self._rows.count():
            item = self._rows.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.deleteLater()
        self._row_refreshers_by_id.clear()

        current = getattr(self._target, self._field) or []
        if not isinstance(current, list):
            return
        for index, sub_obj in enumerate(current):
            self._rows.addWidget(self._build_row(index, sub_obj))

    def _build_row(self, index: int, sub_obj: Any) -> QWidget:
        group = QGroupBox(self._title_for(sub_obj, index))
        outer = QVBoxLayout(group)
        outer.setContentsMargins(8, 12, 8, 8)
        outer.setSpacing(4)

        form_host = QWidget()
        form = QFormLayout(form_host)
        form.setContentsMargins(0, 0, 0, 0)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        refreshers: list[Callable[[], None]] = []
        self._populate(form, sub_obj, refreshers)
        self._row_refreshers_by_id[id(sub_obj)] = refreshers
        outer.addWidget(form_host)

        remove = QPushButton("Remove")
        remove.clicked.connect(lambda _checked=False, obj=sub_obj: self._remove(obj))
        outer.addWidget(remove, alignment=Qt.AlignmentFlag.AlignRight)

        return group

    def _add(self, factory: Callable[[], Any]) -> None:
        self._session.execute(
            AddListItemCommand(self._session, self._target, self._field, factory())
        )

    def _remove(self, sub_obj: Any) -> None:
        self._session.execute(
            RemoveListItemCommand(self._session, self._target, self._field, sub_obj)
        )


class ReferenceListEditor(_ListEditorBase):
    def __init__(
        self,
        target: object,
        field: str,
        session: EditorSession,
        *,
        choices: Callable[[], list[str]],
        accept_single_string: bool = False,
    ) -> None:
        self._choices = choices
        super().__init__(target, field, session, accept_single_string=accept_single_string)

    def _default_value(self) -> Any:
        options = self._choices()
        return options[0] if options else ""

    def _build_input(self, index: int, value: Any) -> QWidget:
        widget = QComboBox()
        widget.setEditable(True)
        widget.addItems(self._choices())
        text = "" if value is None else str(value)
        if text:
            existing = widget.findText(text)
            if existing >= 0:
                widget.setCurrentIndex(existing)
            else:
                widget.setCurrentText(text)
        widget.activated.connect(
            lambda _idx, i=index, w=widget: self._on_changed(i, w.currentText())
        )
        line_edit = widget.lineEdit()
        if line_edit is not None:
            line_edit.editingFinished.connect(
                lambda i=index, w=widget: self._on_changed(i, w.currentText())
            )
        return widget
