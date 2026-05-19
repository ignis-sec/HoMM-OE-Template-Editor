"""EditorSession — owns the current Template and broadcasts changes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal

if TYPE_CHECKING:
    from pathlib import Path

    from templategen.model.template import Template
    from templategen.services.commands import Command


class EditorSession(QObject):
    template_changed = Signal()
    dirty_changed = Signal(bool)
    selection_changed = Signal(object)

    @property
    def template(self) -> Template | None:
        raise NotImplementedError

    @property
    def is_dirty(self) -> bool:
        raise NotImplementedError

    def load(self, path: Path) -> None:
        raise NotImplementedError

    def save(self, path: Path | None = None) -> None:
        raise NotImplementedError

    def execute(self, command: Command) -> None:
        raise NotImplementedError

    def undo(self) -> None:
        raise NotImplementedError

    def redo(self) -> None:
        raise NotImplementedError
