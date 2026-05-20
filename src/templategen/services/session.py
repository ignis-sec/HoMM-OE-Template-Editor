"""EditorSession — owns the current Template, broadcasts changes, runs the undo stack."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QUndoStack

from templategen.io.loader import TemplateLoader
from templategen.io.writer import TemplateWriter

if TYPE_CHECKING:
    from pathlib import Path

    from templategen.model.template import Template
    from templategen.services.commands import Command


class EditorSession(QObject):
    template_changed = Signal()
    current_variant_changed = Signal(int)
    selection_changed = Signal(object)
    dirty_changed = Signal(bool)
    model_object_changed = Signal(object)
    undo_available_changed = Signal(bool)
    redo_available_changed = Signal(bool)

    def __init__(self) -> None:
        super().__init__()
        self._template: Template | None = None
        self._path: Path | None = None
        self._current_variant_index: int = 0
        self._selection: object | None = None

        self._undo_stack = QUndoStack(self)
        self._undo_stack.cleanChanged.connect(self._on_clean_changed)
        self._undo_stack.canUndoChanged.connect(self.undo_available_changed)
        self._undo_stack.canRedoChanged.connect(self.redo_available_changed)

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
        return not self._undo_stack.isClean()

    @property
    def can_undo(self) -> bool:
        return self._undo_stack.canUndo()

    @property
    def can_redo(self) -> bool:
        return self._undo_stack.canRedo()

    def load(self, path: Path) -> None:
        self._template = TemplateLoader().load(path)
        self._path = path
        self._current_variant_index = 0
        self._selection = None
        self._undo_stack.clear()
        self.template_changed.emit()
        self.current_variant_changed.emit(0)
        self.selection_changed.emit(None)
        self.dirty_changed.emit(False)

    def save(self, path: Path | None = None) -> None:
        if self._template is None:
            return
        target = path or self._path
        if target is None:
            raise RuntimeError("No path to save to")
        TemplateWriter().write(self._template, target)
        if path is not None:
            self._path = path
        self._undo_stack.setClean()

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

    def execute(self, command: Command) -> None:
        self._undo_stack.push(command)

    def undo(self) -> None:
        self._undo_stack.undo()

    def redo(self) -> None:
        self._undo_stack.redo()

    def begin_macro(self, text: str) -> None:
        self._undo_stack.beginMacro(text)

    def end_macro(self) -> None:
        self._undo_stack.endMacro()

    def _on_clean_changed(self, clean: bool) -> None:
        self.dirty_changed.emit(not clean)
