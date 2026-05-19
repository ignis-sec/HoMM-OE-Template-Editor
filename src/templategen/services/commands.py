"""Command pattern — every model mutation goes through one of these for undo/redo."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from templategen.services.session import EditorSession


class Command(ABC):
    @abstractmethod
    def do(self, session: EditorSession) -> None: ...

    @abstractmethod
    def undo(self, session: EditorSession) -> None: ...


class AddZoneCommand(Command):
    def do(self, session: EditorSession) -> None:
        raise NotImplementedError

    def undo(self, session: EditorSession) -> None:
        raise NotImplementedError


class RemoveZoneCommand(Command):
    def do(self, session: EditorSession) -> None:
        raise NotImplementedError

    def undo(self, session: EditorSession) -> None:
        raise NotImplementedError


class MoveZoneCommand(Command):
    def do(self, session: EditorSession) -> None:
        raise NotImplementedError

    def undo(self, session: EditorSession) -> None:
        raise NotImplementedError


class ConnectZonesCommand(Command):
    def do(self, session: EditorSession) -> None:
        raise NotImplementedError

    def undo(self, session: EditorSession) -> None:
        raise NotImplementedError


class DisconnectZonesCommand(Command):
    def do(self, session: EditorSession) -> None:
        raise NotImplementedError

    def undo(self, session: EditorSession) -> None:
        raise NotImplementedError


class EditFieldCommand(Command):
    def do(self, session: EditorSession) -> None:
        raise NotImplementedError

    def undo(self, session: EditorSession) -> None:
        raise NotImplementedError
