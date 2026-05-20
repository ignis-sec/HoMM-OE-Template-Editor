"""SidPicker — editable combo with autocomplete, sourced from a catalog callable."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QCompleter

from templategen.services.commands import EditFieldCommand

if TYPE_CHECKING:
    from collections.abc import Callable

    from templategen.services.session import EditorSession


class SidPicker(QComboBox):
    def __init__(
        self,
        target: object,
        field: str,
        session: EditorSession,
        *,
        choices: Callable[[], list[str]],
    ) -> None:
        super().__init__()
        self._target = target
        self._field = field
        self._session = session
        self._choices = choices

        self.setEditable(True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        completer = QCompleter()
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.setCompleter(completer)

        self.refresh()

        self.activated.connect(self._on_commit)
        line = self.lineEdit()
        if line is not None:
            line.editingFinished.connect(self._on_commit)

    def refresh(self) -> None:
        with _block_signals(self):
            current_text = self.currentText()
            current_value = getattr(self._target, self._field)
            text = current_text or ("" if current_value is None else str(current_value))
            self.clear()
            self.addItems(list(self._choices()))
            if text:
                idx = self.findText(text)
                if idx >= 0:
                    self.setCurrentIndex(idx)
                else:
                    self.setEditText(text)

    def _on_commit(self) -> None:
        new = self.currentText() or None
        if new != getattr(self._target, self._field):
            self._session.execute(EditFieldCommand(self._session, self._target, self._field, new))


class _block_signals:  # noqa: N801
    def __init__(self, widget: QComboBox) -> None:
        self._widget = widget
        self._prev = False

    def __enter__(self) -> None:
        self._prev = self._widget.blockSignals(True)

    def __exit__(self, *_exc: object) -> None:
        self._widget.blockSignals(self._prev)
