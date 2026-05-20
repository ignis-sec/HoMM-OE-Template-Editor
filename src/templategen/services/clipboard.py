"""EditorClipboard — in-memory clipboard for model items, shared across documents."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal


class EditorClipboard(QObject):
    contents_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._item: object | None = None

    @property
    def item(self) -> object | None:
        return self._item

    def has_item(self) -> bool:
        return self._item is not None

    def set_item(self, item: object | None) -> None:
        self._item = item
        self.contents_changed.emit()

    def clear(self) -> None:
        self.set_item(None)
