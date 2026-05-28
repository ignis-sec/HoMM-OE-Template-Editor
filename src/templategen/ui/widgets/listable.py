"""Generic value-object for items displayed in dropdowns and list widgets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

    from PySide6.QtGui import QIcon


@dataclass(frozen=True)
class ListableItem:
    """A renderable choice for dropdowns/lists.

    `value` is the canonical string that gets written to the model. `label` is the
    user-facing text; defaults to `value` when not provided. `icon` is an optional
    thumbnail. Widgets that consume `ListableItem` should display `label` + `icon`
    and store/commit `value`.
    """

    value: str
    label: str | None = None
    icon: QIcon | None = None

    @property
    def display(self) -> str:
        return self.label if self.label else self.value


def to_listable(items: Iterable[str | ListableItem]) -> list[ListableItem]:
    """Normalize a mixed iterable of strings or ListableItems into ListableItems."""
    out: list[ListableItem] = []
    for item in items:
        if isinstance(item, ListableItem):
            out.append(item)
        else:
            out.append(ListableItem(value=item))
    return out
