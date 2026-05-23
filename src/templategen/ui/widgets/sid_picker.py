"""SidPicker — editable combo with autocomplete, sourced from a catalog callable.

`choices` can return either bare strings or :class:`ListableItem`s. When ListableItems
provide a label/icon, the combo displays them while still committing the canonical
`value` to the model.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QComboBox

from templategen.services.commands import EditFieldCommand
from templategen.ui.widgets.listable import ListableItem, to_listable

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
        choices: Callable[[], list[str | ListableItem]],
    ) -> None:
        super().__init__()
        self._target = target
        self._field = field
        self._session = session
        self._choices = choices

        self.setEditable(True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        # Use the combo's auto-wired completer (model = combo's item model) and switch it
        # from prefix-match to contains-match so typing part of a name OR sid matches.
        existing = self.completer()
        if existing is not None:
            existing.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            existing.setFilterMode(Qt.MatchFlag.MatchContains)

        self.refresh()

        self.activated.connect(self._on_commit)
        line = self.lineEdit()
        if line is not None:
            line.editingFinished.connect(self._on_commit)

    def refresh(self) -> None:
        with _block_signals(self):
            current_text = self.currentText()
            current_value = getattr(self._target, self._field)
            target_value = current_text or ("" if current_value is None else str(current_value))

            items = to_listable(self._choices())
            if any(i.icon is not None for i in items):
                self.setIconSize(QSize(24, 24))
            self.clear()
            for item in items:
                if item.icon is not None:
                    self.addItem(item.icon, item.display, item.value)
                else:
                    self.addItem(item.display, item.value)

            if target_value:
                matched = -1
                for i in range(self.count()):
                    if self.itemData(i) == target_value:
                        matched = i
                        break
                if matched >= 0:
                    self.setCurrentIndex(matched)
                else:
                    self.setEditText(target_value)

    def _resolved_value(self) -> str | None:
        text = self.currentText()
        idx = self.currentIndex()
        if idx >= 0 and self.itemText(idx) == text:
            data = self.itemData(idx)
            if isinstance(data, str):
                return data or None
        return text or None

    def _on_commit(self) -> None:
        new = self._resolved_value()
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
