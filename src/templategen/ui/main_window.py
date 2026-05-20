"""Main application window — wires menus, toolbar, docks, and status bar."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QCloseEvent, QKeySequence
from PySide6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from templategen.catalog.builder import CatalogBuildError, build_snapshot, write_snapshot
from templategen.catalog.game_data import GameDataCatalog
from templategen.services.session import EditorSession
from templategen.ui.canvas.graph_scene import GraphScene
from templategen.ui.canvas.graph_view import GraphView
from templategen.ui.dialogs.template_settings import TemplateSettingsDialog
from templategen.ui.icons import IconRegistry
from templategen.ui.panels.explorer import CatalogExplorer
from templategen.ui.panels.inspector import Inspector
from templategen.ui.panels.library import LibraryPanel
from templategen.ui.panels.variant_tabs import VariantTabBar


class MainWindow(QMainWindow):
    def __init__(self, session: EditorSession, icons: IconRegistry, catalog: GameDataCatalog) -> None:
        super().__init__()
        self._session = session
        self._icons = icons
        self._catalog = catalog

        self.setWindowTitle("TemplateGenerator")
        self.resize(1400, 900)

        self._build_actions()
        self._build_central()
        self._build_menus()
        self._build_toolbar()
        self._build_docks()
        self._build_statusbar()

        session.template_changed.connect(self._on_template_changed)
        session.current_variant_changed.connect(self._update_variant_label)
        session.dirty_changed.connect(self._update_title)
        session.undo_available_changed.connect(self.action_undo.setEnabled)
        session.redo_available_changed.connect(self.action_redo.setEnabled)

        self.action_undo.setEnabled(False)
        self.action_redo.setEnabled(False)
        self.action_save.setEnabled(True)

    def _build_actions(self) -> None:
        self.action_new = QAction(self._icons.get("new"), "&New Template", self)
        self.action_new.setShortcut(QKeySequence.StandardKey.New)
        self.action_new.triggered.connect(self._not_implemented)

        self.action_open = QAction(self._icons.get("open"), "&Open…", self)
        self.action_open.setShortcut(QKeySequence.StandardKey.Open)
        self.action_open.triggered.connect(self._on_open)

        self.action_save = QAction(self._icons.get("save"), "&Save", self)
        self.action_save.setShortcut(QKeySequence.StandardKey.Save)
        self.action_save.triggered.connect(self._on_save)

        self.action_save_as = QAction(self._icons.get("save_as"), "Save &As…", self)
        self.action_save_as.setShortcut(QKeySequence.StandardKey.SaveAs)
        self.action_save_as.triggered.connect(self._on_save_as)

        self.action_exit = QAction(self._icons.get("exit"), "E&xit", self)
        self.action_exit.setShortcut(QKeySequence.StandardKey.Quit)
        self.action_exit.triggered.connect(self.close)

        self.action_undo = QAction(self._icons.get("undo"), "&Undo", self)
        self.action_undo.setShortcut(QKeySequence.StandardKey.Undo)
        self.action_undo.triggered.connect(self._session.undo)

        self.action_redo = QAction(self._icons.get("redo"), "&Redo", self)
        self.action_redo.setShortcut(QKeySequence.StandardKey.Redo)
        self.action_redo.triggered.connect(self._session.redo)

        self.action_add_variant = QAction(self._icons.get("add_variant"), "&Add Variant", self)
        self.action_add_variant.triggered.connect(self._not_implemented)

        self.action_remove_variant = QAction(self._icons.get("remove_variant"), "&Remove Current Variant", self)
        self.action_remove_variant.triggered.connect(self._not_implemented)

        self.action_validate = QAction(self._icons.get("validate"), "&Validate", self)
        self.action_validate.setShortcut("F5")
        self.action_validate.triggered.connect(self._not_implemented)

        self.action_template_settings = QAction(self._icons.get("settings"), "Template &Settings…", self)
        self.action_template_settings.triggered.connect(self._on_template_settings)

        self.action_rebuild_catalog = QAction("&Rebuild Catalog from game-data…", self)
        self.action_rebuild_catalog.triggered.connect(self._on_rebuild_catalog)

        self.action_reload_catalog = QAction("Re&load Catalog snapshot", self)
        self.action_reload_catalog.triggered.connect(self._on_reload_catalog)

        self.action_show_explorer = QAction("Show &Catalog Explorer", self)
        self.action_show_explorer.triggered.connect(self._on_show_explorer)

        self.action_about = QAction(self._icons.get("about"), "&About TemplateGenerator", self)
        self.action_about.triggered.connect(self._show_about)

        self.action_about_qt = QAction("About &Qt", self)
        self.action_about_qt.triggered.connect(lambda: QMessageBox.aboutQt(self))

    def _build_central(self) -> None:
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._variant_tabs = VariantTabBar(self._session)
        self._graph_scene = GraphScene(self._session)
        self._graph_view = GraphView(self._graph_scene)

        layout.addWidget(self._variant_tabs)
        layout.addWidget(self._graph_view, stretch=1)

        self.setCentralWidget(central)

    def _build_menus(self) -> None:
        bar = self.menuBar()

        menu_file = bar.addMenu("&File")
        menu_file.addAction(self.action_new)
        menu_file.addAction(self.action_open)
        self.menu_recent = menu_file.addMenu("Open &Recent")
        self.menu_recent.setEnabled(False)
        menu_file.addSeparator()
        menu_file.addAction(self.action_save)
        menu_file.addAction(self.action_save_as)
        menu_file.addSeparator()
        menu_file.addAction(self.action_exit)

        menu_edit = bar.addMenu("&Edit")
        menu_edit.addAction(self.action_undo)
        menu_edit.addAction(self.action_redo)

        self.menu_view = bar.addMenu("&View")

        menu_template = bar.addMenu("&Template")
        menu_template.addAction(self.action_add_variant)
        menu_template.addAction(self.action_remove_variant)
        menu_template.addSeparator()
        menu_template.addAction(self.action_validate)
        menu_template.addAction(self.action_template_settings)

        menu_tools = bar.addMenu("&Tools")
        menu_tools.addAction(self.action_show_explorer)
        menu_tools.addSeparator()
        menu_tools.addAction(self.action_rebuild_catalog)
        menu_tools.addAction(self.action_reload_catalog)

        menu_help = bar.addMenu("&Help")
        menu_help.addAction(self.action_about)
        menu_help.addAction(self.action_about_qt)

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Main", self)
        toolbar.setMovable(False)
        toolbar.setIconSize(toolbar.iconSize() * 0.9)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)

        toolbar.addAction(self.action_new)
        toolbar.addAction(self.action_open)
        toolbar.addAction(self.action_save)
        toolbar.addSeparator()
        toolbar.addAction(self.action_undo)
        toolbar.addAction(self.action_redo)
        toolbar.addSeparator()
        toolbar.addAction(self.action_validate)

    def _build_docks(self) -> None:
        self._library_dock = self._make_dock(
            "Library",
            LibraryPanel(self._session),
            Qt.DockWidgetArea.LeftDockWidgetArea,
        )
        self._inspector_dock = self._make_dock(
            "Inspector",
            Inspector(self._session, self._catalog),
            Qt.DockWidgetArea.RightDockWidgetArea,
        )
        self._explorer = CatalogExplorer(self._catalog)
        self._explorer_dock = self._make_dock(
            "Catalog Explorer",
            self._explorer,
            Qt.DockWidgetArea.BottomDockWidgetArea,
            allowed_areas=Qt.DockWidgetArea.AllDockWidgetAreas,
        )
        self._explorer_dock.setVisible(False)

        self.menu_view.addAction(self._library_dock.toggleViewAction())
        self.menu_view.addAction(self._inspector_dock.toggleViewAction())
        self.menu_view.addAction(self._explorer_dock.toggleViewAction())

    def _make_dock(
        self,
        title: str,
        content: QWidget,
        area: Qt.DockWidgetArea,
        *,
        allowed_areas: Qt.DockWidgetArea | None = None,
    ) -> QDockWidget:
        dock = QDockWidget(title, self)
        dock.setWidget(content)
        if allowed_areas is None:
            allowed_areas = Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        dock.setAllowedAreas(allowed_areas)
        self.addDockWidget(area, dock)
        return dock

    def _build_statusbar(self) -> None:
        bar = self.statusBar()
        bar.showMessage("Ready")
        self._variant_label = QLabel("No template")
        bar.addPermanentWidget(self._variant_label)

    def _on_open(self) -> None:
        if not self._confirm_discard_changes():
            return
        examples = Path.cwd() / "example-templates"
        default_dir = str(examples if examples.exists() else Path.cwd())
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Template",
            default_dir,
            "RMG Templates (*.rmg.json);;All Files (*)",
        )
        if not path:
            return
        try:
            self._session.load(Path(path))
        except Exception as exc:
            QMessageBox.critical(self, "Open failed", f"Could not load template:\n\n{exc}")

    def _on_save(self) -> None:
        if self._session.template is None:
            return
        if self._session.path is None:
            self._on_save_as()
            return
        try:
            self._session.save()
            self.statusBar().showMessage(f"Saved {self._session.path.name}", 3000)
        except Exception as exc:
            QMessageBox.critical(self, "Save failed", f"Could not save:\n\n{exc}")

    def _on_save_as(self) -> None:
        if self._session.template is None:
            return
        default = str(self._session.path or Path.cwd())
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Template As",
            default,
            "RMG Templates (*.rmg.json);;All Files (*)",
        )
        if not path:
            return
        try:
            self._session.save(Path(path))
            self.statusBar().showMessage(f"Saved {Path(path).name}", 3000)
        except Exception as exc:
            QMessageBox.critical(self, "Save failed", f"Could not save:\n\n{exc}")

    def _confirm_discard_changes(self) -> bool:
        if not self._session.is_dirty:
            return True
        choice = QMessageBox.question(
            self,
            "Unsaved changes",
            "You have unsaved changes. Save before continuing?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
        if choice == QMessageBox.StandardButton.Save:
            self._on_save()
            return not self._session.is_dirty
        return choice == QMessageBox.StandardButton.Discard

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._confirm_discard_changes():
            event.accept()
        else:
            event.ignore()

    def _on_template_changed(self) -> None:
        template = self._session.template
        path = self._session.path
        name = path.name if path else "Untitled"
        if template is not None:
            self.statusBar().showMessage(
                f"Loaded {name}: {len(template.variants)} variant(s), {len(template.zoneLayouts)} layout(s)",
                4000,
            )
        self._update_variant_label()
        self._update_title()

    def _update_title(self, _dirty: bool | None = None) -> None:
        path = self._session.path
        name = path.name if path else "TemplateGenerator"
        suffix = " *" if self._session.is_dirty else ""
        self.setWindowTitle(f"TemplateGenerator — {name}{suffix}" if path else f"TemplateGenerator{suffix}")

    def _update_variant_label(self, _index: int | None = None) -> None:
        template = self._session.template
        if template is None or not template.variants:
            self._variant_label.setText("No template")
            return
        cur = self._session.current_variant_index + 1
        total = len(template.variants)
        self._variant_label.setText(f"Variant {cur} of {total}")

    def _on_template_settings(self) -> None:
        if self._session.template is None:
            self.statusBar().showMessage("Open a template first", 2500)
            return
        dialog = TemplateSettingsDialog(self._session, self._session.template, self._catalog, self)
        dialog.exec()

    def _on_rebuild_catalog(self) -> None:
        default_dir = str(Path.cwd() / "game-data" / "Core")
        if not Path(default_dir).exists():
            default_dir = str(Path.cwd())
        chosen = QFileDialog.getExistingDirectory(self, "Locate the game's Core folder", default_dir)
        if not chosen:
            return
        try:
            snapshot = build_snapshot(Path(chosen))
            write_snapshot(snapshot, self._catalog.snapshot_path)
        except (CatalogBuildError, OSError) as exc:
            QMessageBox.critical(self, "Catalog rebuild failed", str(exc))
            return
        self._catalog.reload()
        self.statusBar().showMessage(
            f"Catalog rebuilt: {len(snapshot['sids'])} SIDs, "
            f"{len(snapshot['content_lists'])} lists, "
            f"{len(snapshot['content_pools'])} pools",
            5000,
        )

    def _on_reload_catalog(self) -> None:
        self._catalog.reload()
        if self._catalog.is_loaded():
            self.statusBar().showMessage("Catalog reloaded from snapshot", 3000)
        else:
            self.statusBar().showMessage("Catalog snapshot missing or empty", 4000)

    def _on_show_explorer(self) -> None:
        self._explorer_dock.setVisible(True)
        self._explorer_dock.raise_()
        self._explorer_dock.activateWindow()

    def _not_implemented(self) -> None:
        self.statusBar().showMessage("Not implemented yet", 2500)

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "About TemplateGenerator",
            "<h3>TemplateGenerator</h3>"
            "<p>Graphical editor for Heroes of Might and Magic: Olden Era random-map templates.</p>",
        )
