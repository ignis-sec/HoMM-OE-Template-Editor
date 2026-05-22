"""Command pattern — every model mutation goes through one of these for undo/redo."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QPointF
from PySide6.QtGui import QUndoCommand

if TYPE_CHECKING:
    from templategen.services.session import EditorSession
    from templategen.ui.canvas.graph_scene import GraphScene


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


class AddListItemCommand(Command):
    def __init__(
        self,
        session: EditorSession,
        owner: object,
        field: str,
        item: Any,
        text: str | None = None,
    ) -> None:
        super().__init__(session, text or f"Add {type(item).__name__}")
        self._owner = owner
        self._field = field
        self._item = item

    def redo(self) -> None:
        getattr(self._owner, self._field).append(self._item)
        self._session.model_object_changed.emit(self._owner)

    def undo(self) -> None:
        getattr(self._owner, self._field).remove(self._item)
        self._session.model_object_changed.emit(self._owner)


class RemoveListItemCommand(Command):
    def __init__(
        self,
        session: EditorSession,
        owner: object,
        field: str,
        item: Any,
        text: str | None = None,
    ) -> None:
        super().__init__(session, text or f"Remove {type(item).__name__}")
        self._owner = owner
        self._field = field
        self._item = item
        self._index: int | None = None

    def redo(self) -> None:
        collection: list[Any] = getattr(self._owner, self._field)
        self._index = collection.index(self._item)
        collection.pop(self._index)
        self._session.model_object_changed.emit(self._owner)

    def undo(self) -> None:
        if self._index is None:
            return
        getattr(self._owner, self._field).insert(self._index, self._item)
        self._session.model_object_changed.emit(self._owner)


class AddVariantCommand(Command):
    def __init__(
        self,
        session: EditorSession,
        template: Any,
        variant: Any,
        text: str | None = None,
    ) -> None:
        super().__init__(session, text or "Add variant")
        self._template = template
        self._variant = variant
        self._prev_index: int | None = None

    def redo(self) -> None:
        self._prev_index = self._session.current_variant_index
        self._template.variants.append(self._variant)
        self._session.model_object_changed.emit(self._template)
        self._session.set_current_variant_index(len(self._template.variants) - 1)

    def undo(self) -> None:
        if self._variant in self._template.variants:
            self._template.variants.remove(self._variant)
        if self._prev_index is not None and self._template.variants:
            target = min(self._prev_index, len(self._template.variants) - 1)
            self._session.set_current_variant_index(target)
        self._session.model_object_changed.emit(self._template)


class RemoveVariantCommand(Command):
    def __init__(
        self,
        session: EditorSession,
        template: Any,
        index: int,
        text: str | None = None,
    ) -> None:
        super().__init__(session, text or f"Remove variant {index + 1}")
        self._template = template
        self._index = index
        self._removed: Any = None
        self._prev_current: int | None = None

    def redo(self) -> None:
        if not 0 <= self._index < len(self._template.variants):
            return
        self._prev_current = self._session.current_variant_index
        self._removed = self._template.variants.pop(self._index)
        if self._template.variants:
            new_current = min(self._prev_current, len(self._template.variants) - 1)
            self._session.set_current_variant_index(new_current)
        self._session.model_object_changed.emit(self._template)

    def undo(self) -> None:
        if self._removed is None:
            return
        self._template.variants.insert(self._index, self._removed)
        if self._prev_current is not None:
            self._session.set_current_variant_index(self._prev_current)
        self._session.model_object_changed.emit(self._template)


class AddZoneCommand(Command):
    def __init__(
        self,
        session: EditorSession,
        variant: Any,
        zone: Any,
        text: str | None = None,
    ) -> None:
        super().__init__(session, text or f"Add zone {zone.name}")
        self._variant = variant
        self._zone = zone

    def redo(self) -> None:
        self._variant.zones.append(self._zone)
        self._session.model_object_changed.emit(self._variant)
        self._session.set_selection(self._zone)

    def undo(self) -> None:
        if self._zone in self._variant.zones:
            self._variant.zones.remove(self._zone)
        self._session.model_object_changed.emit(self._variant)
        self._session.set_selection(None)


class RemoveZoneCommand(Command):
    def __init__(
        self,
        session: EditorSession,
        variant: Any,
        zone: Any,
        text: str | None = None,
    ) -> None:
        super().__init__(session, text or f"Remove zone {zone.name}")
        self._variant = variant
        self._zone = zone
        self._index: int | None = None

    def redo(self) -> None:
        self._index = self._variant.zones.index(self._zone)
        self._variant.zones.pop(self._index)
        self._session.model_object_changed.emit(self._variant)
        if self._session.selection is self._zone:
            self._session.set_selection(None)

    def undo(self) -> None:
        if self._index is None:
            return
        self._variant.zones.insert(self._index, self._zone)
        self._session.model_object_changed.emit(self._variant)


class AddConnectionCommand(Command):
    def __init__(
        self,
        session: EditorSession,
        variant: Any,
        connection: Any,
        text: str | None = None,
    ) -> None:
        label = connection.name or f"{connection.from_}→{connection.to}"
        super().__init__(session, text or f"Add connection {label}")
        self._variant = variant
        self._connection = connection

    def redo(self) -> None:
        self._variant.connections.append(self._connection)
        self._session.model_object_changed.emit(self._variant)
        self._session.set_selection(self._connection)

    def undo(self) -> None:
        if self._connection in self._variant.connections:
            self._variant.connections.remove(self._connection)
        self._session.model_object_changed.emit(self._variant)
        self._session.set_selection(None)


class MoveZoneCommand(Command):
    """Restores a ZoneItem's canvas position; positions aren't persisted in the model."""

    def __init__(
        self,
        session: EditorSession,
        scene: GraphScene,
        zone_name: str,
        old_pos: QPointF,
        new_pos: QPointF,
        text: str | None = None,
    ) -> None:
        super().__init__(session, text or f"Move zone {zone_name}")
        self._scene = scene
        self._zone_name = zone_name
        self._old = QPointF(old_pos)
        self._new = QPointF(new_pos)
        self._first_redo = True

    def redo(self) -> None:
        # The drag itself already left the item at _new, so skip the initial redo;
        # subsequent redos (after an undo) apply the move explicitly.
        if self._first_redo:
            self._first_redo = False
            return
        self._apply(self._new)

    def undo(self) -> None:
        self._apply(self._old)

    def _apply(self, pos: QPointF) -> None:
        items = getattr(self._scene, "zone_items", None)
        if items is None:
            return
        item = items.get(self._zone_name)
        if item is not None:
            item.setPos(pos)


class ChangeConnectionTypeCommand(Command):
    def __init__(
        self,
        session: EditorSession,
        variant: Any,
        connection: Any,
        new_class: type,
        text: str | None = None,
    ) -> None:
        super().__init__(session, text or f"Change connection to {new_class.__name__}")
        self._variant = variant
        self._old = connection
        self._new_class = new_class
        self._new: Any = None
        self._index: int | None = None

    def redo(self) -> None:
        self._index = self._variant.connections.index(self._old)
        if self._new is None:
            self._new = _migrate_connection(self._old, self._new_class)
        self._variant.connections[self._index] = self._new
        self._session.model_object_changed.emit(self._variant)
        self._session.set_selection(self._new)

    def undo(self) -> None:
        if self._index is None:
            return
        self._variant.connections[self._index] = self._old
        self._session.model_object_changed.emit(self._variant)
        self._session.set_selection(self._old)


def _migrate_connection(old: Any, new_class: type) -> Any:
    data = old.model_dump(by_alias=True, exclude_unset=True)
    data.pop("connectionType", None)
    allowed: set[str] = set()
    for field_name, field_info in new_class.model_fields.items():
        allowed.add(field_name)
        if field_info.alias:
            allowed.add(field_info.alias)
    filtered = {k: v for k, v in data.items() if k in allowed}
    return new_class.model_validate(filtered)


class RemoveConnectionCommand(Command):
    def __init__(
        self,
        session: EditorSession,
        variant: Any,
        connection: Any,
        text: str | None = None,
    ) -> None:
        label = connection.name or f"{connection.from_}→{connection.to}"
        super().__init__(session, text or f"Remove connection {label}")
        self._variant = variant
        self._connection = connection
        self._index: int | None = None

    def redo(self) -> None:
        self._index = self._variant.connections.index(self._connection)
        self._variant.connections.pop(self._index)
        self._session.model_object_changed.emit(self._variant)
        if self._session.selection is self._connection:
            self._session.set_selection(None)

    def undo(self) -> None:
        if self._index is None:
            return
        self._variant.connections.insert(self._index, self._connection)
        self._session.model_object_changed.emit(self._variant)
