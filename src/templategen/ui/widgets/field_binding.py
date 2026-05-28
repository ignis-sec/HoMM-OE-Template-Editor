"""Two-way bindings between Qt widgets and model fields, routed through EditFieldCommand."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING

from templategen.services.commands import EditFieldCommand, UnsetFieldCommand

if TYPE_CHECKING:
    from PySide6.QtWidgets import QCheckBox, QComboBox, QDoubleSpinBox, QLineEdit, QSpinBox

    from templategen.services.session import EditorSession

Refresh = Callable[[], None]


def bind_string(
    widget: QLineEdit,
    target: object,
    field: str,
    session: EditorSession,
    *,
    optional: bool = False,
) -> Refresh:
    def from_model() -> str:
        value = getattr(target, field)
        return "" if value is None else str(value)

    def to_model() -> str | None:
        text = widget.text()
        if optional and not text:
            return None
        return text

    widget.setText(from_model())

    def on_commit() -> None:
        new = to_model()
        if new != getattr(target, field):
            session.execute(EditFieldCommand(session, target, field, new))

    def refresh() -> None:
        text = from_model()
        if widget.text() != text:
            widget.setText(text)

    widget.editingFinished.connect(on_commit)
    return refresh


def bind_int(
    widget: QSpinBox,
    target: object,
    field: str,
    session: EditorSession,
) -> Refresh:
    current = getattr(target, field)
    widget.setValue(int(current) if current is not None else 0)

    def on_commit() -> None:
        new = widget.value()
        if new != getattr(target, field):
            session.execute(EditFieldCommand(session, target, field, new))

    def refresh() -> None:
        current = getattr(target, field)
        new = int(current) if current is not None else 0
        if widget.value() != new:
            widget.blockSignals(True)
            widget.setValue(new)
            widget.blockSignals(False)

    widget.editingFinished.connect(on_commit)
    return refresh


def bind_int_optional(
    widget: QSpinBox,
    target: object,
    field: str,
    session: EditorSession,
    *,
    sentinel: int,
) -> Refresh:
    """Two-way bind a spinbox where `sentinel` (typically `minimum`, paired with
    `setSpecialValueText("(none)")`) maps to the field being absent from
    `model_fields_set` so the writer omits it from JSON."""

    def from_model() -> int:
        current = getattr(target, field)
        return sentinel if current is None else int(current)

    widget.blockSignals(True)
    widget.setValue(from_model())
    widget.blockSignals(False)

    def on_commit() -> None:
        value = widget.value()
        current = getattr(target, field)
        if value == sentinel:
            if current is not None or field in target.__pydantic_fields_set__:
                session.execute(UnsetFieldCommand(session, target, field))
        elif value != current:
            session.execute(EditFieldCommand(session, target, field, value))

    def refresh() -> None:
        new = from_model()
        if widget.value() != new:
            widget.blockSignals(True)
            widget.setValue(new)
            widget.blockSignals(False)

    widget.editingFinished.connect(on_commit)
    return refresh


def bind_float(
    widget: QDoubleSpinBox,
    target: object,
    field: str,
    session: EditorSession,
) -> Refresh:
    current = getattr(target, field)
    widget.setValue(float(current) if current is not None else 0.0)

    def on_commit() -> None:
        new = widget.value()
        if new != getattr(target, field):
            session.execute(EditFieldCommand(session, target, field, new))

    def refresh() -> None:
        current = getattr(target, field)
        new = float(current) if current is not None else 0.0
        if widget.value() != new:
            widget.blockSignals(True)
            widget.setValue(new)
            widget.blockSignals(False)

    widget.editingFinished.connect(on_commit)
    return refresh


def bind_bool(
    widget: QCheckBox,
    target: object,
    field: str,
    session: EditorSession,
) -> Refresh:
    current = getattr(target, field)
    widget.setChecked(bool(current))

    def on_commit(checked: bool) -> None:
        if checked != bool(getattr(target, field) or False):
            session.execute(EditFieldCommand(session, target, field, checked))

    def refresh() -> None:
        current = bool(getattr(target, field) or False)
        if widget.isChecked() != current:
            widget.blockSignals(True)
            widget.setChecked(current)
            widget.blockSignals(False)

    widget.clicked.connect(on_commit)
    return refresh


def bind_choice(
    widget: QComboBox,
    target: object,
    field: str,
    session: EditorSession,
    choices: Iterable[str],
) -> Refresh:
    widget.clear()
    widget.addItems(list(choices))
    current = getattr(target, field)
    if current is not None:
        idx = widget.findText(str(current))
        if idx >= 0:
            widget.setCurrentIndex(idx)

    def on_commit(_index: int) -> None:
        new = widget.currentText()
        if new != getattr(target, field):
            session.execute(EditFieldCommand(session, target, field, new))

    def refresh() -> None:
        current = getattr(target, field)
        text = "" if current is None else str(current)
        if widget.currentText() != text:
            idx = widget.findText(text)
            if idx >= 0:
                widget.blockSignals(True)
                widget.setCurrentIndex(idx)
                widget.blockSignals(False)

    widget.activated.connect(on_commit)
    return refresh
