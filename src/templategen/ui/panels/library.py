"""LibraryPanel — read-only tree of the template's content libraries."""

from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

from templategen.services.session import EditorSession


class LibraryPanel(QWidget):
    def __init__(self, session: EditorSession) -> None:
        super().__init__()
        self._session = session
        self.setMinimumWidth(240)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        layout.addWidget(self._tree)

        session.template_changed.connect(self._rebuild)

    def _rebuild(self) -> None:
        self._tree.clear()
        template = self._session.template
        if template is None:
            return

        layouts = QTreeWidgetItem(self._tree, ["Zone Layouts"])
        for zl in template.zoneLayouts:
            QTreeWidgetItem(layouts, [zl.name])

        bundles = QTreeWidgetItem(self._tree, ["Mandatory Content"])
        for bundle in template.mandatoryContent:
            QTreeWidgetItem(bundles, [bundle.name])

        limits = QTreeWidgetItem(self._tree, ["Content Count Limits"])
        for limit in template.contentCountLimits:
            QTreeWidgetItem(limits, [limit.name])

        self._tree.expandAll()
