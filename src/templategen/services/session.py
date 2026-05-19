"""EditorSession — owns the current Template and broadcasts changes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal

from templategen.io.loader import TemplateLoader

if TYPE_CHECKING:
    from pathlib import Path

    from templategen.model.template import Template
    from templategen.services.commands import Command


class EditorSession(QObject):
    template_changed = Signal()
    current_variant_changed = Signal(int)
    selection_changed = Signal(object)
    dirty_changed = Signal(bool)

    def __init__(self) -> None:
        super().__init__()
        self._template: Template | None = None
        self._path: Path | None = None
        self._current_variant_index: int = 0
        self._selection: object | None = None

    @property
    def template(self) -> Template | None:
        return self._template

    @property
    def path(self) -> Path | None:
        return self._path

    @property
    def current_variant_index(self) -> int:
        return self._current_variant_index

    @property
    def selection(self) -> object | None:
        return self._selection

    @property
    def is_dirty(self) -> bool:
        return False

    def load(self, path: Path) -> None:
        self._template = TemplateLoader().load(path)
        self._path = path
        self._current_variant_index = 0
        self._selection = None
        self.template_changed.emit()
        self.current_variant_changed.emit(0)
        self.selection_changed.emit(None)

    def set_current_variant_index(self, index: int) -> None:
        if index == self._current_variant_index:
            return
        self._current_variant_index = index
        self._selection = None
        self.current_variant_changed.emit(index)
        self.selection_changed.emit(None)

    def set_selection(self, target: object | None) -> None:
        if target is self._selection:
            return
        self._selection = target
        self.selection_changed.emit(target)

    def save(self, path: Path | None = None) -> None:
        raise NotImplementedError

    def execute(self, command: Command) -> None:
        raise NotImplementedError

    def undo(self) -> None:
        raise NotImplementedError

    def redo(self) -> None:
        raise NotImplementedError
