"""LibraryPanel — browse and edit zoneLayouts, mandatoryContent, contentCountLimits."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeyEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QMenu,
    QMessageBox,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from templategen.model.content import ContentCountLimit, MandatoryContentBundle
from templategen.model.layouts import ZoneLayout
from templategen.model.template import Template
from templategen.services.commands import (
    AddListItemCommand,
    RemoveListItemCommand,
    RenameLibraryItemCommand,
)
from templategen.services.naming import unique_name

if TYPE_CHECKING:
    from templategen.services.clipboard import EditorClipboard
    from templategen.services.workspace import Workspace

_NAME_COLUMN = 0
_BRANCH_ROLE = Qt.ItemDataRole.UserRole + 1
_MODEL_ROLE = Qt.ItemDataRole.UserRole + 2

_FIELD_FOR_TYPE: dict[type, str] = {
    ZoneLayout: "zoneLayouts",
    MandatoryContentBundle: "mandatoryContent",
    ContentCountLimit: "contentCountLimits",
}


class LibraryPanel(QWidget):
    def __init__(self, workspace: Workspace, clipboard: EditorClipboard) -> None:
        super().__init__()
        self._session = workspace
        self._clipboard = clipboard
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

        workspace.template_changed.connect(self._rebuild)
        workspace.model_object_changed.connect(self._on_model_changed)

        self._update_buttons_enabled()

    # ─── Tree building ────────────────────────────────────────────────────

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

    # ─── Context menu ─────────────────────────────────────────────────────

    def _on_context_menu(self, pos: object) -> None:
        item = self._tree.itemAt(pos)
        menu = QMenu(self)

        model = item.data(_NAME_COLUMN, _MODEL_ROLE) if item is not None else None
        if model is not None:
            cut_action = QAction("Cut", self)
            cut_action.setShortcut("Ctrl+X")
            cut_action.triggered.connect(lambda: self._cut(item))
            menu.addAction(cut_action)

            copy_action = QAction("Copy", self)
            copy_action.setShortcut("Ctrl+C")
            copy_action.triggered.connect(lambda: self._copy(item))
            menu.addAction(copy_action)

        paste_action = QAction("Paste", self)
        paste_action.setShortcut("Ctrl+V")
        paste_action.setEnabled(self._can_paste())
        paste_action.triggered.connect(self.paste)
        menu.addAction(paste_action)

        if model is not None:
            menu.addSeparator()
            rename_action = QAction("Rename…", self)
            rename_action.triggered.connect(lambda: self._rename(item))
            menu.addAction(rename_action)
            duplicate_action = QAction("Duplicate", self)
            duplicate_action.triggered.connect(lambda: self._duplicate(item))
            menu.addAction(duplicate_action)
            remove_action = QAction("Remove", self)
            remove_action.triggered.connect(lambda: self._remove_item(item))
            menu.addAction(remove_action)

        if menu.isEmpty():
            return
        menu.exec(self._tree.viewport().mapToGlobal(pos))

    # ─── Keyboard / public actions ────────────────────────────────────────

    def copy_selected(self) -> None:
        item = self._selected_item()
        if item is not None:
            self._copy(item)

    def cut_selected(self) -> None:
        item = self._selected_item()
        if item is not None:
            self._cut(item)

    def duplicate_selected(self) -> None:
        item = self._selected_item()
        if item is not None:
            self._duplicate(item)

    def delete_selected(self) -> None:
        item = self._selected_item()
        if item is not None:
            self._remove_item(item)

    def paste(self) -> None:
        if not self._can_paste() or self._session.template is None:
            return
        source = self._clipboard.item
        assert source is not None
        field = _FIELD_FOR_TYPE.get(type(source))
        if field is None:
            return
        new_item = source.model_copy(deep=True)
        new_item.name = self._unique_in_field(field, new_item.name)
        self._session.execute(
            AddListItemCommand(
                self._session,
                self._session.template,
                field,
                new_item,
                f"Paste {new_item.name}",
            )
        )
        self._select_model(new_item)

    # ─── Per-item operations ──────────────────────────────────────────────

    def _copy(self, item: QTreeWidgetItem) -> None:
        model = item.data(_NAME_COLUMN, _MODEL_ROLE)
        if model is not None:
            self._clipboard.set_item(model.model_copy(deep=True))

    def _cut(self, item: QTreeWidgetItem) -> None:
        model = item.data(_NAME_COLUMN, _MODEL_ROLE)
        if model is None:
            return
        self._clipboard.set_item(model.model_copy(deep=True))
        self._remove_item(item)

    def _rename(self, item: QTreeWidgetItem) -> None:
        model = item.data(_NAME_COLUMN, _MODEL_ROLE)
        parent = item.parent()
        template = self._session.template
        if model is None or parent is None or template is None:
            return
        field = parent.data(_NAME_COLUMN, _BRANCH_ROLE)
        old_name = getattr(model, "name", "")
        new_name, ok = QInputDialog.getText(
            self,
            "Rename",
            f"New name for '{old_name}':",
            text=old_name,
        )
        if not ok:
            return
        new_name = new_name.strip()
        if not new_name or new_name == old_name:
            return
        existing = {n for n in self._existing_names(field) if n != old_name}
        if new_name in existing:
            QMessageBox.warning(
                self,
                "Name in use",
                f"'{new_name}' is already used by another {parent.text(_NAME_COLUMN).split(' (')[0].lower()} item.",
            )
            return
        self._session.execute(
            RenameLibraryItemCommand(
                self._session,
                template,
                model,
                new_name,
                f"Rename {old_name} → {new_name}",
            )
        )

    def _duplicate(self, item: QTreeWidgetItem) -> None:
        model = item.data(_NAME_COLUMN, _MODEL_ROLE)
        parent = item.parent()
        if model is None or parent is None or self._session.template is None:
            return
        field = parent.data(_NAME_COLUMN, _BRANCH_ROLE)
        new_item = model.model_copy(deep=True)
        new_item.name = self._unique_in_field(field, new_item.name)
        self._session.execute(
            AddListItemCommand(
                self._session,
                self._session.template,
                field,
                new_item,
                f"Duplicate {new_item.name}",
            )
        )
        self._select_model(new_item)

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

    # ─── Library Add buttons (existing) ───────────────────────────────────

    def _add_zone_layout(self) -> None:
        template = self._session.template
        if template is None:
            return
        name = unique_name("new_zone_layout", [zl.name for zl in template.zoneLayouts])
        new_item = ZoneLayout(name=name)
        self._session.execute(
            AddListItemCommand(self._session, template, "zoneLayouts", new_item, f"Add zone layout {name}")
        )
        self._select_model(new_item)

    def _add_mandatory_content(self) -> None:
        template = self._session.template
        if template is None:
            return
        name = unique_name("new_content", [b.name for b in template.mandatoryContent])
        new_item = MandatoryContentBundle(name=name)
        self._session.execute(
            AddListItemCommand(self._session, template, "mandatoryContent", new_item, f"Add content bundle {name}")
        )
        self._select_model(new_item)

    def _add_content_count_limit(self) -> None:
        template = self._session.template
        if template is None:
            return
        name = unique_name("new_limit", [c.name for c in template.contentCountLimits])
        new_item = ContentCountLimit(name=name)
        self._session.execute(
            AddListItemCommand(self._session, template, "contentCountLimits", new_item, f"Add count limit {name}")
        )
        self._select_model(new_item)

    # ─── Helpers ──────────────────────────────────────────────────────────

    def _select_model(self, model: object) -> None:
        item = self._items_by_model_id.get(id(model))
        if item is None:
            return
        self._tree.setCurrentItem(item)
        self._tree.scrollToItem(item)

    def _selected_item(self) -> QTreeWidgetItem | None:
        items = self._tree.selectedItems()
        if not items:
            return None
        item = items[0]
        if item.data(_NAME_COLUMN, _MODEL_ROLE) is None:
            return None
        return item

    def _can_paste(self) -> bool:
        if not self._clipboard.has_item() or self._session.template is None:
            return False
        return type(self._clipboard.item) in _FIELD_FOR_TYPE

    def _unique_in_field(self, field: str, desired: str) -> str:
        existing = self._existing_names(field)
        if desired not in existing:
            return desired
        base = desired if desired.endswith("_copy") else f"{desired}_copy"
        if base not in existing:
            return base
        i = 1
        while f"{base}_{i}" in existing:
            i += 1
        return f"{base}_{i}"

    def _existing_names(self, field: str) -> list[str]:
        template = self._session.template
        if template is None:
            return []
        return [getattr(x, "name", "") for x in getattr(template, field, [])]


class _LibraryTree(QTreeWidget):
    def __init__(self, panel: LibraryPanel) -> None:
        super().__init__()
        self._panel = panel

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_C:
                self._panel.copy_selected()
                event.accept()
                return
            if event.key() == Qt.Key.Key_X:
                self._panel.cut_selected()
                event.accept()
                return
            if event.key() == Qt.Key.Key_V:
                self._panel.paste()
                event.accept()
                return
            if event.key() == Qt.Key.Key_D:
                self._panel.duplicate_selected()
                event.accept()
                return
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self._panel.delete_selected()
            event.accept()
            return
        super().keyPressEvent(event)
