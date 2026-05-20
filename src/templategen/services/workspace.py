"""Workspace — manages multiple open Documents and proxies the active session's API."""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal

from templategen.services.session import EditorSession

if TYPE_CHECKING:
    from pathlib import Path

    from templategen.model.template import Template
    from templategen.services.clipboard import EditorClipboard
    from templategen.services.commands import Command


@dataclass
class Document:
    session: EditorSession


class Workspace(QObject):
    template_changed = Signal()
    current_variant_changed = Signal(int)
    selection_changed = Signal(object)
    dirty_changed = Signal(bool)
    model_object_changed = Signal(object)
    undo_available_changed = Signal(bool)
    redo_available_changed = Signal(bool)

    document_added = Signal(object)
    document_removed = Signal(object)
    current_document_changed = Signal(object)

    def __init__(self, clipboard: EditorClipboard | None = None) -> None:
        super().__init__()
        self._documents: list[Document] = []
        self._current: Document | None = None
        self._clipboard = clipboard

    @property
    def documents(self) -> list[Document]:
        return list(self._documents)

    @property
    def current(self) -> Document | None:
        return self._current

    @property
    def clipboard(self) -> EditorClipboard | None:
        return self._clipboard

    @property
    def template(self) -> Template | None:
        return self._current.session.template if self._current else None

    @property
    def path(self) -> Path | None:
        return self._current.session.path if self._current else None

    @property
    def current_variant_index(self) -> int:
        return self._current.session.current_variant_index if self._current else 0

    @property
    def selection(self) -> object | None:
        return self._current.session.selection if self._current else None

    @property
    def is_dirty(self) -> bool:
        return self._current.session.is_dirty if self._current else False

    @property
    def can_undo(self) -> bool:
        return self._current.session.can_undo if self._current else False

    @property
    def can_redo(self) -> bool:
        return self._current.session.can_redo if self._current else False

    def execute(self, command: Command) -> None:
        if self._current is not None:
            self._current.session.execute(command)

    def undo(self) -> None:
        if self._current is not None:
            self._current.session.undo()

    def redo(self) -> None:
        if self._current is not None:
            self._current.session.redo()

    def begin_macro(self, text: str) -> None:
        if self._current is not None:
            self._current.session.begin_macro(text)

    def end_macro(self) -> None:
        if self._current is not None:
            self._current.session.end_macro()

    def set_current_variant_index(self, index: int) -> None:
        if self._current is not None:
            self._current.session.set_current_variant_index(index)

    def set_selection(self, target: object | None) -> None:
        if self._current is not None:
            self._current.session.set_selection(target)

    def save(self, path: Path | None = None) -> None:
        if self._current is not None:
            self._current.session.save(path)

    def new_document(self) -> Document:
        doc = Document(EditorSession())
        self._documents.append(doc)
        self.document_added.emit(doc)
        self.set_current(doc)
        return doc

    def open_document(self, path: Path) -> Document:
        session = EditorSession()
        session.load(path)
        doc = Document(session)
        self._documents.append(doc)
        self.document_added.emit(doc)
        self.set_current(doc)
        return doc

    def close_document(self, doc: Document) -> bool:
        if doc not in self._documents:
            return False
        if doc is self._current:
            self.set_current(self._next_after(doc))
        self._documents.remove(doc)
        self.document_removed.emit(doc)
        return True

    def set_current(self, doc: Document | None) -> None:
        if doc is self._current:
            return
        self._disconnect_current()
        self._current = doc
        self._connect_current()
        self.current_document_changed.emit(doc)
        self._reemit_session_signals()

    def _next_after(self, doc: Document) -> Document | None:
        if len(self._documents) <= 1:
            return None
        idx = self._documents.index(doc)
        return self._documents[1] if idx == 0 else self._documents[idx - 1]

    def _connect_current(self) -> None:
        if self._current is None:
            return
        s = self._current.session
        s.template_changed.connect(self.template_changed)
        s.current_variant_changed.connect(self.current_variant_changed)
        s.selection_changed.connect(self.selection_changed)
        s.dirty_changed.connect(self.dirty_changed)
        s.model_object_changed.connect(self.model_object_changed)
        s.undo_available_changed.connect(self.undo_available_changed)
        s.redo_available_changed.connect(self.redo_available_changed)

    def _disconnect_current(self) -> None:
        if self._current is None:
            return
        s = self._current.session
        for source, target in (
            (s.template_changed, self.template_changed),
            (s.current_variant_changed, self.current_variant_changed),
            (s.selection_changed, self.selection_changed),
            (s.dirty_changed, self.dirty_changed),
            (s.model_object_changed, self.model_object_changed),
            (s.undo_available_changed, self.undo_available_changed),
            (s.redo_available_changed, self.redo_available_changed),
        ):
            with contextlib.suppress(RuntimeError):
                source.disconnect(target)

    def _reemit_session_signals(self) -> None:
        self.template_changed.emit()
        if self._current is not None:
            s = self._current.session
            self.current_variant_changed.emit(s.current_variant_index)
            self.selection_changed.emit(s.selection)
            self.dirty_changed.emit(s.is_dirty)
            self.undo_available_changed.emit(s.can_undo)
            self.redo_available_changed.emit(s.can_redo)
        else:
            self.current_variant_changed.emit(0)
            self.selection_changed.emit(None)
            self.dirty_changed.emit(False)
            self.undo_available_changed.emit(False)
            self.redo_available_changed.emit(False)
