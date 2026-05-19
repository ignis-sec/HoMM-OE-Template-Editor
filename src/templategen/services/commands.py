"""Command pattern — every model mutation goes through one of these for undo/redo."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PySide6.QtGui import QUndoCommand

if TYPE_CHECKING:
    from templategen.services.session import EditorSession


class Command(QUndoCommand):
    def __init__(self, session: EditorSession, text: str) -> None:
        super().__init__(text)
        self._session = session


class EditFieldCommand(Command):
    def __init__(
        self,
        session: EditorSession,
        target: object,
        field: str,
        new_value: Any,
        text: str | None = None,
    ) -> None:
        super().__init__(session, text or f"Edit {field}")
        self._target = target
        self._field = field
        self._new = new_value
        self._old = getattr(target, field)

    def redo(self) -> None:
        setattr(self._target, self._field, self._new)
        self._session.model_object_changed.emit(self._target)

    def undo(self) -> None:
        setattr(self._target, self._field, self._old)
        self._session.model_object_changed.emit(self._target)


class AddZoneCommand(Command):
    def redo(self) -> None:
        raise NotImplementedError

    def undo(self) -> None:
        raise NotImplementedError


class RemoveZoneCommand(Command):
    def redo(self) -> None:
        raise NotImplementedError

    def undo(self) -> None:
        raise NotImplementedError


class MoveZoneCommand(Command):
    def redo(self) -> None:
        raise NotImplementedError

    def undo(self) -> None:
        raise NotImplementedError


class ConnectZonesCommand(Command):
    def redo(self) -> None:
        raise NotImplementedError

    def undo(self) -> None:
        raise NotImplementedError


class DisconnectZonesCommand(Command):
    def redo(self) -> None:
        raise NotImplementedError

    def undo(self) -> None:
        raise NotImplementedError
