"""LibraryPanel — browse and edit zoneLayouts, mandatoryContent, contentCountLimits."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeyEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMenu,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from templategen.model.content import ContentCountLimit, MandatoryContentBundle
from templategen.model.layouts import ZoneLayout
from templategen.model.template import Template
from templategen.services.commands import AddListItemCommand, RemoveListItemCommand

if TYPE_CHECKING:
    from templategen.services.session import EditorSession

_NAME_COLUMN = 0
_BRANCH_ROLE = Qt.ItemDataRole.UserRole + 1
_MODEL_ROLE = Qt.ItemDataRole.UserRole + 2


class LibraryPanel(QWidget):
    def __init__(self, session: EditorSession) -> None:
        super().__init__()
        self._session = session
        self._items_by_model_id: dict[int, QTreeWidgetItem] = {}

        self.setMinimumWidth(260)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(4, 4, 4, 4)
        outer.setSpacing(4)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(4)
        self._btn_add_layout = QPushButton("+ Layout")
        self._btn_add_bundle = QPushButton("+ Bundle")
        self._btn_add_limit = QPushButton("+ Limit")
        toolbar.addWidget(self._btn_add_layout)
        toolbar.addWidget(self._btn_add_bundle)
        toolbar.addWidget(self._btn_add_limit)
        toolbar.addStretch()
        outer.addLayout(toolbar)

        self._tree = _LibraryTree(self)
        self._tree.setHeaderHidden(True)
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        outer.addWidget(self._tree)

        self._btn_add_layout.clicked.connect(self._add_zone_layout)
        self._btn_add_bundle.clicked.connect(self._add_mandatory_content)
        self._btn_add_limit.clicked.connect(self._add_content_count_limit)
        self._tree.itemSelectionChanged.connect(self._on_tree_selection_changed)
        self._tree.customContextMenuRequested.connect(self._on_context_menu)

        session.template_changed.connect(self._rebuild)
        session.model_object_changed.connect(self._on_model_changed)

        self._update_buttons_enabled()

    def _rebuild(self) -> None:
        self._tree.blockSignals(True)
        self._tree.clear()
        self._items_by_model_id.clear()
        template = self._session.template

        self._layouts_root = self._make_branch("Zone Layouts", "zoneLayouts")
        self._bundles_root = self._make_branch("Mandatory Content", "mandatoryContent")
        self._limits_root = self._make_branch("Content Count Limits", "contentCountLimits")

        if template is not None:
            for layout in template.zoneLayouts:
                self._add_tree_item(self._layouts_root, layout)
            for bundle in template.mandatoryContent:
                self._add_tree_item(self._bundles_root, bundle)
            for limit in template.contentCountLimits:
                self._add_tree_item(self._limits_root, limit)

        self._tree.expandAll()
        self._update_branch_counts()
        self._tree.blockSignals(False)
        self._update_buttons_enabled()

    def _make_branch(self, label: str, field: str) -> QTreeWidgetItem:
        root = QTreeWidgetItem(self._tree, [label])
        root.setData(_NAME_COLUMN, _BRANCH_ROLE, field)
        root.setFlags(Qt.ItemFlag.ItemIsEnabled)
        return root

    def _add_tree_item(self, parent: QTreeWidgetItem, model: object) -> QTreeWidgetItem:
        item = QTreeWidgetItem(parent, [getattr(model, "name", "?")])
        item.setData(_NAME_COLUMN, _MODEL_ROLE, model)
        self._items_by_model_id[id(model)] = item
        return item

    def _update_branch_counts(self) -> None:
        for root, label in (
            (self._layouts_root, "Zone Layouts"),
            (self._bundles_root, "Mandatory Content"),
            (self._limits_root, "Content Count Limits"),
        ):
            root.setText(_NAME_COLUMN, f"{label} ({root.childCount()})")

    def _update_buttons_enabled(self) -> None:
        has_template = self._session.template is not None
        self._btn_add_layout.setEnabled(has_template)
        self._btn_add_bundle.setEnabled(has_template)
        self._btn_add_limit.setEnabled(has_template)

    def _on_tree_selection_changed(self) -> None:
        items = self._tree.selectedItems()
        if not items:
            return
        model = items[0].data(_NAME_COLUMN, _MODEL_ROLE)
        if model is not None:
            self._session.set_selection(model)

    def _on_model_changed(self, obj: object) -> None:
        if isinstance(obj, Template):
            self._rebuild()
            return
        item = self._items_by_model_id.get(id(obj))
        if item is not None:
            item.setText(_NAME_COLUMN, getattr(obj, "name", "?"))

    def _on_context_menu(self, pos: object) -> None:
        item = self._tree.itemAt(pos)
        if item is None or item.data(_NAME_COLUMN, _MODEL_ROLE) is None:
            return
        menu = QMenu(self)
        remove_action = QAction("Remove", self)
        remove_action.triggered.connect(lambda: self._remove_item(item))
        menu.addAction(remove_action)
        menu.exec(self._tree.viewport().mapToGlobal(pos))

    def delete_selected(self) -> None:
        items = self._tree.selectedItems()
        if not items:
            return
        item = items[0]
        if item.data(_NAME_COLUMN, _MODEL_ROLE) is None:
            return
        self._remove_item(item)

    def _remove_item(self, item: QTreeWidgetItem) -> None:
        model = item.data(_NAME_COLUMN, _MODEL_ROLE)
        if model is None or self._session.template is None:
            return
        parent = item.parent()
        if parent is None:
            return
        field = parent.data(_NAME_COLUMN, _BRANCH_ROLE)
        self._session.execute(
            RemoveListItemCommand(
                self._session,
                self._session.template,
                field,
                model,
                f"Remove {model.name}",
            )
        )

    def _add_zone_layout(self) -> None:
        template = self._session.template
        if template is None:
            return
        name = _unique_name("new_zone_layout", [zl.name for zl in template.zoneLayouts])
        self._session.execute(
            AddListItemCommand(
                self._session,
                template,
                "zoneLayouts",
                ZoneLayout(name=name),
                f"Add zone layout {name}",
            )
        )

    def _add_mandatory_content(self) -> None:
        template = self._session.template
        if template is None:
            return
        name = _unique_name("new_content", [b.name for b in template.mandatoryContent])
        self._session.execute(
            AddListItemCommand(
                self._session,
                template,
                "mandatoryContent",
                MandatoryContentBundle(name=name),
                f"Add content bundle {name}",
            )
        )

    def _add_content_count_limit(self) -> None:
        template = self._session.template
        if template is None:
            return
        name = _unique_name("new_limit", [c.name for c in template.contentCountLimits])
        self._session.execute(
            AddListItemCommand(
                self._session,
                template,
                "contentCountLimits",
                ContentCountLimit(name=name),
                f"Add count limit {name}",
            )
        )


class _LibraryTree(QTreeWidget):
    def __init__(self, panel: LibraryPanel) -> None:
        super().__init__()
        self._panel = panel

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self._panel.delete_selected()
            event.accept()
            return
        super().keyPressEvent(event)


def _unique_name(base: str, existing: list[str]) -> str:
    if base not in existing:
        return base
    i = 1
    while f"{base}_{i}" in existing:
        i += 1
    return f"{base}_{i}"
