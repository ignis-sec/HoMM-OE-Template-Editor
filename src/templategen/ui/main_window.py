"""Main application window — multi-document, side docks bound to the workspace."""

from __future__ import annotations

import contextlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QAction, QCloseEvent, QKeySequence
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDockWidget,
    QFileDialog,
    QFormLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QTabWidget,
    QTextBrowser,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from templategen.io.template_image import render_template_png, template_png_path
from templategen.model.enums import OrientationMode
from templategen.model.variant import Orientation, Variant
from templategen.services.commands import AddVariantCommand, RemoveVariantCommand
from templategen.services.validator import Validator
from templategen.ui.asset_icons import sid_listables
from templategen.ui.canvas.graph_scene import GraphScene
from templategen.ui.canvas.graph_view import GraphView
from templategen.ui.dialogs.first_run import rebuild_catalog_interactive
from templategen.ui.dialogs.log_window import LogWindow
from templategen.ui.dialogs.template_settings import TemplateSettingsDialog
from templategen.ui.dialogs.validation_results import ValidationResultsDialog
from templategen.ui.metadata import CHANGELOG, VERSION
from templategen.ui.panels.explorer import CatalogExplorer
from templategen.ui.panels.inspector import Inspector
from templategen.ui.panels.library import LibraryPanel
from templategen.ui.panels.variant_tabs import VariantTabBar

if TYPE_CHECKING:
    from templategen.catalog.game_data import GameDataCatalog
    from templategen.services.clipboard import EditorClipboard
    from templategen.services.workspace import Document, Workspace
    from templategen.ui.icons import IconRegistry


_log = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(
        self,
        workspace: Workspace,
        icons: IconRegistry,
        catalog: GameDataCatalog,
        clipboard: EditorClipboard,
    ) -> None:
        super().__init__()
        self._workspace = workspace
        self._icons = icons
        self._catalog = catalog
        self._clipboard = clipboard
        self._tab_for_document: dict[int, _DocumentTab] = {}
        self._log_window: LogWindow | None = None
        self._current_view: GraphView | None = None

        self.setWindowTitle("HoMM:OE Template Editor")
        self.resize(1400, 900)

        self._build_actions()
        self._build_central()
        self._build_menus()
        self._build_toolbar()
        self._build_docks()
        self._build_statusbar()

        workspace.template_changed.connect(self._on_template_changed)
        workspace.current_variant_changed.connect(self._update_variant_label)
        workspace.dirty_changed.connect(self._update_title)
        workspace.undo_available_changed.connect(self.action_undo.setEnabled)
        workspace.redo_available_changed.connect(self.action_redo.setEnabled)
        workspace.document_added.connect(self._on_document_added)
        workspace.document_removed.connect(self._on_document_removed)
        workspace.current_document_changed.connect(self._on_current_document_changed)

        self.action_undo.setEnabled(False)
        self.action_redo.setEnabled(False)
        self._update_canvas_actions_enabled(False)
        self._update_title()
        self._update_variant_label()

        # qdarktheme's stylesheet makes the first combo-with-icons addRow cost
        # ~500 ms (Qt polishes every icon). Pay that cost offscreen right after
        # the main window paints, so the first Template Settings dialog opens
        # without the freeze.
        self._icon_polish_warmer: QWidget | None = None
        QTimer.singleShot(0, self._prewarm_icon_polish)

    def _prewarm_icon_polish(self) -> None:
        if not self._catalog.is_loaded():
            return
        items = sid_listables(self._catalog, list(self._catalog.known_sids()))
        if not any(i.icon is not None for i in items):
            return
        host = QWidget()
        form = QFormLayout(host)
        combo = QComboBox()
        combo.setEditable(True)
        combo.setIconSize(QSize(24, 24))
        for it in items:
            if it.icon is not None:
                combo.addItem(it.icon, it.display, it.value)
            else:
                combo.addItem(it.display, it.value)
        form.addRow("warm", combo)
        self._icon_polish_warmer = host

    def _build_actions(self) -> None:
        self.action_new = QAction(self._icons.get("new"), "&New Template", self)
        self.action_new.setShortcut(QKeySequence.StandardKey.New)
        self.action_new.triggered.connect(self._on_new)

        self.action_open = QAction(self._icons.get("open"), "&Open…", self)
        self.action_open.setShortcut(QKeySequence.StandardKey.Open)
        self.action_open.triggered.connect(self._on_open)

        self.action_close_tab = QAction("&Close Tab", self)
        self.action_close_tab.setShortcut(QKeySequence.StandardKey.Close)
        self.action_close_tab.triggered.connect(self._on_close_current_tab)

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
        self.action_undo.triggered.connect(self._workspace.undo)

        self.action_redo = QAction(self._icons.get("redo"), "&Redo", self)
        self.action_redo.setShortcut(QKeySequence.StandardKey.Redo)
        self.action_redo.triggered.connect(self._workspace.redo)

        self.action_add_variant = QAction(self._icons.get("add_variant"), "&Add Variant", self)
        self.action_add_variant.triggered.connect(self._on_add_variant)

        self.action_remove_variant = QAction(self._icons.get("remove_variant"), "&Remove Current Variant", self)
        self.action_remove_variant.triggered.connect(self._on_remove_variant)

        self.action_add_zone = QAction(self._icons.get("add_zone"), "Add &Zone", self)
        self.action_add_zone.setCheckable(True)
        self.action_add_zone.setShortcut("Ctrl+Shift+Z")
        self.action_add_zone.toggled.connect(self._on_toggle_place)

        self.action_connect = QAction(self._icons.get("connect"), "&Connect Zones", self)
        self.action_connect.setCheckable(True)
        self.action_connect.setShortcut("Ctrl+L")
        self.action_connect.toggled.connect(self._on_toggle_connect)

        self.action_delete = QAction(self._icons.get("delete"), "&Delete Selection", self)
        self.action_delete.triggered.connect(self._on_delete_selection)

        self.action_validate = QAction(self._icons.get("validate"), "&Validate", self)
        self.action_validate.setShortcut("F5")
        self.action_validate.triggered.connect(self._on_validate)

        self.action_template_settings = QAction(self._icons.get("settings"), "Template &Settings…", self)
        self.action_template_settings.triggered.connect(self._on_template_settings)

        self.action_rebuild_catalog = QAction("&Rebuild Catalog from game install…", self)
        self.action_rebuild_catalog.triggered.connect(self._on_rebuild_catalog)

        self.action_reload_catalog = QAction("Re&load Catalog snapshot", self)
        self.action_reload_catalog.triggered.connect(self._on_reload_catalog)

        self.action_show_explorer = QAction("Show &Catalog Explorer", self)
        self.action_show_explorer.triggered.connect(self._on_show_explorer)

        self.action_show_log = QAction("Show &Log Window", self)
        self.action_show_log.setShortcut("Ctrl+Shift+L")
        self.action_show_log.triggered.connect(self._on_show_log)

        self.action_show_roads = QAction(self._icons.get("roads"), "Toggle &Road Graph", self)
        self.action_show_roads.setCheckable(True)
        self.action_show_roads.setShortcut("Ctrl+R")
        self.action_show_roads.setToolTip("Toggle road graph view (Ctrl+R)")
        self.action_show_roads.toggled.connect(self._on_toggle_show_roads)

        self.action_show_all_objects = QAction(
            self._icons.get("show_all_objects"), "Show All Bundle &Objects", self
        )
        self.action_show_all_objects.setCheckable(True)
        self.action_show_all_objects.setShortcut("Ctrl+Shift+R")
        self.action_show_all_objects.setEnabled(False)
        self.action_show_all_objects.setToolTip(
            "In road graph view, also draw bundle ContentItems that no road points at yet "
            "(Ctrl+Shift+R)"
        )
        self.action_show_all_objects.toggled.connect(self._on_toggle_show_all_objects)

        self.action_add_road = QAction(self._icons.get("add_road"), "&Add Road", self)
        self.action_add_road.setCheckable(True)
        self.action_add_road.setShortcut("Ctrl+Alt+R")
        self.action_add_road.setEnabled(False)
        self.action_add_road.setToolTip(
            "Click two nodes in the road graph to create the connecting road(s) (Ctrl+Alt+R)"
        )
        self.action_add_road.toggled.connect(self._on_toggle_add_road)

        self.action_about = QAction(self._icons.get("about"), "&About HoMM:OE Template Editor", self)
        self.action_about.triggered.connect(self._show_about)

        self.action_about_qt = QAction("About &Qt", self)
        self.action_about_qt.triggered.connect(lambda: QMessageBox.aboutQt(self))

    def _build_central(self) -> None:
        self._tabs = QTabWidget()
        self._tabs.setTabsClosable(True)
        self._tabs.setMovable(True)
        self._tabs.setDocumentMode(True)
        self._tabs.tabCloseRequested.connect(self._on_tab_close_requested)
        self._tabs.currentChanged.connect(self._on_tab_changed)

        self._empty_placeholder = QLabel("No template open. Use File → Open or File → New.")
        self._empty_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_placeholder.setStyleSheet("color: #888; font-size: 14px;")

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._tabs)
        layout.addWidget(self._empty_placeholder)
        self._tabs.setVisible(False)
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
        menu_file.addAction(self.action_close_tab)
        menu_file.addAction(self.action_exit)

        menu_edit = bar.addMenu("&Edit")
        menu_edit.addAction(self.action_undo)
        menu_edit.addAction(self.action_redo)
        menu_edit.addSeparator()
        menu_edit.addAction(self.action_add_zone)
        menu_edit.addAction(self.action_connect)
        menu_edit.addAction(self.action_delete)

        self.menu_view = bar.addMenu("&View")

        menu_template = bar.addMenu("&Template")
        menu_template.addAction(self.action_add_variant)
        menu_template.addAction(self.action_remove_variant)
        menu_template.addSeparator()
        menu_template.addAction(self.action_validate)
        menu_template.addAction(self.action_template_settings)

        menu_tools = bar.addMenu("&Tools")
        menu_tools.addAction(self.action_show_explorer)
        menu_tools.addAction(self.action_show_log)
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
        toolbar.addAction(self.action_add_zone)
        toolbar.addAction(self.action_connect)
        toolbar.addAction(self.action_delete)
        toolbar.addSeparator()
        toolbar.addAction(self.action_validate)
        toolbar.addAction(self.action_show_roads)
        toolbar.addAction(self.action_show_all_objects)
        toolbar.addAction(self.action_add_road)

    def _build_docks(self) -> None:
        self._library_dock = self._make_dock(
            "Library",
            LibraryPanel(self._workspace, self._clipboard),
            Qt.DockWidgetArea.LeftDockWidgetArea,
        )
        self._inspector_dock = self._make_dock(
            "Inspector",
            Inspector(self._workspace, self._catalog),
            Qt.DockWidgetArea.RightDockWidgetArea,
        )
        # The catalog explorer is expensive to construct (~1.5 s of Qt layout work for
        # the ~1800 list-widget items across all eight tabs). It's hidden by default, so
        # we build it lazily the first time the user opens it — keeps startup snappy.
        self._explorer: CatalogExplorer | None = None
        self._explorer_dock: QDockWidget | None = None

        self.menu_view.addAction(self._library_dock.toggleViewAction())
        self.menu_view.addAction(self._inspector_dock.toggleViewAction())

    def _ensure_explorer_dock(self) -> QDockWidget:
        if self._explorer_dock is not None and self._explorer is not None:
            return self._explorer_dock
        self._explorer = CatalogExplorer(self._catalog)
        self._explorer_dock = self._make_dock(
            "Catalog Explorer",
            self._explorer,
            Qt.DockWidgetArea.BottomDockWidgetArea,
            allowed_areas=Qt.DockWidgetArea.AllDockWidgetAreas,
        )
        self.menu_view.addAction(self._explorer_dock.toggleViewAction())
        return self._explorer_dock

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

    def _on_document_added(self, document: Document) -> None:
        tab = _DocumentTab(document, self._catalog)
        self._tab_for_document[id(document)] = tab
        tab.scene.set_show_roads(self.action_show_roads.isChecked())
        tab.scene.set_show_all_objects(self.action_show_all_objects.isChecked())
        idx = self._tabs.addTab(tab, self._tab_title_for(document))
        document.session.dirty_changed.connect(lambda _dirty, d=document: self._refresh_tab_title(d))
        document.session.template_changed.connect(lambda d=document: self._refresh_tab_title(d))
        self._tabs.setVisible(True)
        self._empty_placeholder.setVisible(False)
        self._tabs.setCurrentIndex(idx)

    def _on_document_removed(self, document: Document) -> None:
        tab = self._tab_for_document.pop(id(document), None)
        if tab is None:
            return
        idx = self._tabs.indexOf(tab)
        if idx >= 0:
            self._tabs.removeTab(idx)
        if self._tabs.count() == 0:
            self._tabs.setVisible(False)
            self._empty_placeholder.setVisible(True)

    def _on_current_document_changed(self, document: Document | None) -> None:
        self._rebind_current_view(document)
        if document is None:
            self._update_canvas_actions_enabled(False)
            return
        tab = self._tab_for_document.get(id(document))
        if tab is None:
            return
        idx = self._tabs.indexOf(tab)
        if idx >= 0 and self._tabs.currentIndex() != idx:
            self._tabs.setCurrentIndex(idx)
        self._update_canvas_actions_enabled(True)

    def _rebind_current_view(self, document: Document | None) -> None:
        if self._current_view is not None:
            with contextlib.suppress(TypeError, RuntimeError):
                self._current_view.connect_mode_changed.disconnect(self._sync_connect_action)
            with contextlib.suppress(TypeError, RuntimeError):
                self._current_view.place_mode_changed.disconnect(self._sync_place_action)
            with contextlib.suppress(TypeError, RuntimeError):
                self._current_view.road_mode_changed.disconnect(self._sync_road_action)
            with contextlib.suppress(TypeError, RuntimeError):
                self._current_view.road_failed.disconnect(self._on_road_failed)
        self._current_view = None
        if document is None:
            self._sync_connect_action(False)
            self._sync_place_action(False)
            self._sync_road_action(False)
            return
        tab = self._tab_for_document.get(id(document))
        if tab is None:
            return
        self._current_view = tab.view
        self._current_view.connect_mode_changed.connect(self._sync_connect_action)
        self._current_view.place_mode_changed.connect(self._sync_place_action)
        self._current_view.road_mode_changed.connect(self._sync_road_action)
        self._current_view.road_failed.connect(self._on_road_failed)
        self._sync_connect_action(self._current_view.connect_mode)
        self._sync_place_action(self._current_view.place_mode)
        self._sync_road_action(self._current_view.road_mode)

    def _sync_connect_action(self, enabled: bool) -> None:
        if self.action_connect.isChecked() == enabled:
            return
        self.action_connect.blockSignals(True)
        self.action_connect.setChecked(enabled)
        self.action_connect.blockSignals(False)

    def _sync_road_action(self, enabled: bool) -> None:
        if self.action_add_road.isChecked() == enabled:
            return
        self.action_add_road.blockSignals(True)
        self.action_add_road.setChecked(enabled)
        self.action_add_road.blockSignals(False)

    def _sync_place_action(self, enabled: bool) -> None:
        if self.action_add_zone.isChecked() == enabled:
            return
        self.action_add_zone.blockSignals(True)
        self.action_add_zone.setChecked(enabled)
        self.action_add_zone.blockSignals(False)

    def _update_canvas_actions_enabled(self, enabled: bool) -> None:
        self.action_add_zone.setEnabled(enabled)
        self.action_connect.setEnabled(enabled)
        self.action_delete.setEnabled(enabled)

    def _on_tab_changed(self, index: int) -> None:
        if index < 0:
            self._workspace.set_current(None)
            return
        tab = self._tabs.widget(index)
        if isinstance(tab, _DocumentTab):
            self._workspace.set_current(tab.document)

    def _on_tab_close_requested(self, index: int) -> None:
        tab = self._tabs.widget(index)
        if not isinstance(tab, _DocumentTab):
            return
        if not self._confirm_discard_for(tab.document):
            return
        self._workspace.close_document(tab.document)

    def _tab_title_for(self, document: Document) -> str:
        name = document.session.path.name if document.session.path else "Untitled"
        return f"{name}{'*' if document.session.is_dirty else ''}"

    def _refresh_tab_title(self, document: Document) -> None:
        tab = self._tab_for_document.get(id(document))
        if tab is None:
            return
        idx = self._tabs.indexOf(tab)
        if idx >= 0:
            self._tabs.setTabText(idx, self._tab_title_for(document))

    def _on_new(self) -> None:
        self._workspace.new_document()

    def _on_open(self) -> None:
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
            self._workspace.open_document(Path(path))
        except Exception as exc:
            _log.exception("open_document failed for %s", path)
            QMessageBox.critical(self, "Open failed", f"Could not load template:\n\n{exc}")

    def _on_close_current_tab(self) -> None:
        idx = self._tabs.currentIndex()
        if idx >= 0:
            self._on_tab_close_requested(idx)

    def _on_save(self) -> None:
        current = self._workspace.current
        if current is None:
            return
        if current.session.path is None:
            self._on_save_as()
            return
        try:
            self._workspace.save()
            self._export_template_png(current.session.path)
            self.statusBar().showMessage(f"Saved {current.session.path.name}", 3000)
        except Exception as exc:
            _log.exception("save failed for %s", current.session.path)
            QMessageBox.critical(self, "Save failed", f"Could not save:\n\n{exc}")

    def _on_save_as(self) -> None:
        current = self._workspace.current
        if current is None:
            return
        default = str(current.session.path or Path.cwd())
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Template As",
            default,
            "RMG Templates (*.rmg.json);;All Files (*)",
        )
        if not path:
            return
        try:
            self._workspace.save(Path(path))
            self._export_template_png(Path(path))
            self.statusBar().showMessage(f"Saved {Path(path).name}", 3000)
            current_doc = self._workspace.current
            if current_doc is not None:
                self._refresh_tab_title(current_doc)
        except Exception as exc:
            _log.exception("save-as failed for %s", path)
            QMessageBox.critical(self, "Save failed", f"Could not save:\n\n{exc}")

    def _export_template_png(self, rmg_path: Path) -> None:
        template = self._workspace.template
        if template is None:
            return
        zone_positions: dict[str, tuple[float, float]] | None = None
        road_node_positions: dict[str, tuple[float, float]] | None = None
        if self._current_view is not None:
            scene = self._current_view.scene()
            zone_getter = getattr(scene, "current_zone_positions", None)
            if callable(zone_getter):
                zp = zone_getter()
                if zp:
                    zone_positions = zp
            road_getter = getattr(scene, "current_road_node_positions", None)
            if callable(road_getter):
                rp = road_getter()
                if rp:
                    road_node_positions = rp
        try:
            render_template_png(
                template,
                template_png_path(rmg_path),
                variant_index=self._workspace.current_variant_index,
                zone_positions=zone_positions,
                road_node_positions=road_node_positions,
            )
        except (OSError, FileNotFoundError) as exc:
            _log.exception("PNG export failed for %s", template_png_path(rmg_path))
            self.statusBar().showMessage(f"PNG export failed: {exc}", 4000)

    def _confirm_discard_for(self, document: Document) -> bool:
        if not document.session.is_dirty:
            return True
        name = document.session.path.name if document.session.path else "Untitled"
        choice = QMessageBox.question(
            self,
            "Unsaved changes",
            f"'{name}' has unsaved changes. Save before closing?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
        if choice == QMessageBox.StandardButton.Save:
            self._workspace.set_current(document)
            self._on_save()
            return not document.session.is_dirty
        return choice == QMessageBox.StandardButton.Discard

    def closeEvent(self, event: QCloseEvent) -> None:
        for doc in self._workspace.documents:
            if not self._confirm_discard_for(doc):
                _log.info("close cancelled by user (unsaved changes)")
                event.ignore()
                return
        _log.info("main window closing")
        event.accept()

    def _on_toggle_place(self, checked: bool) -> None:
        if self._current_view is None:
            self._sync_place_action(False)
            return
        if checked and self._workspace.template is None:
            self.statusBar().showMessage("Open a template first", 2500)
            self._sync_place_action(False)
            return
        self._current_view.set_place_mode(checked)
        if checked:
            template = self._workspace.template
            if template is not None and not template.zoneLayouts:
                self.statusBar().showMessage(
                    "New zones will be created with no layout — add a Zone Layout in the Library, then assign it.",
                    5000,
                )
            else:
                self.statusBar().showMessage("Click on the canvas to place a new zone (Esc to cancel)", 4000)

    def _on_toggle_connect(self, checked: bool) -> None:
        if self._current_view is not None:
            self._current_view.set_connect_mode(checked)

    def _on_delete_selection(self) -> None:
        if self._current_view is not None:
            self._current_view.delete_selected()

    def _on_add_variant(self) -> None:
        template = self._workspace.template
        if template is None:
            self.statusBar().showMessage("Open a template first", 2500)
            return
        variant = Variant(orientation=Orientation(mode=OrientationMode.MINIMAL_BOUNDING_SQUARE))
        self._workspace.execute(AddVariantCommand(self._workspace, template, variant))

    def _on_remove_variant(self) -> None:
        template = self._workspace.template
        if template is None:
            self.statusBar().showMessage("Open a template first", 2500)
            return
        if len(template.variants) <= 1:
            QMessageBox.information(
                self,
                "Cannot remove variant",
                "A template must have at least one variant.",
            )
            return
        idx = self._workspace.current_variant_index
        self._workspace.execute(RemoveVariantCommand(self._workspace, template, idx))

    def _on_validate(self) -> None:
        template = self._workspace.template
        if template is None:
            self.statusBar().showMessage("Open a template first", 2500)
            return
        issues = Validator().validate(template)
        dialog = ValidationResultsDialog(issues, self._workspace.set_selection, self)
        dialog.exec()

    def _on_template_settings(self) -> None:
        if self._workspace.template is None:
            self.statusBar().showMessage("Open a template first", 2500)
            return
        dialog = TemplateSettingsDialog(self._workspace, self._workspace.template, self._catalog, self)
        dialog.exec()

    def _on_rebuild_catalog(self) -> None:
        if not rebuild_catalog_interactive(self):
            return
        self._catalog.reload()
        if self._catalog.is_loaded():
            self.statusBar().showMessage("Catalog rebuilt from game install", 4000)
        else:
            self.statusBar().showMessage("Catalog build failed (see log)", 4000)

    def _on_reload_catalog(self) -> None:
        self._catalog.reload()
        if self._catalog.is_loaded():
            self.statusBar().showMessage("Catalog reloaded from snapshot", 3000)
        else:
            self.statusBar().showMessage("Catalog snapshot missing or empty", 4000)

    def _on_show_explorer(self) -> None:
        dock = self._ensure_explorer_dock()
        dock.setVisible(True)
        dock.raise_()
        dock.activateWindow()

    def _on_show_log(self) -> None:
        if self._log_window is None:
            self._log_window = LogWindow(self)
        self._log_window.show()
        self._log_window.raise_()
        self._log_window.activateWindow()

    def _on_toggle_show_roads(self, on: bool) -> None:
        self.action_show_all_objects.setEnabled(on)
        self.action_add_road.setEnabled(on)
        if not on:
            if self.action_show_all_objects.isChecked():
                self.action_show_all_objects.setChecked(False)
            if self.action_add_road.isChecked():
                self.action_add_road.setChecked(False)
        for tab in self._tab_for_document.values():
            tab.scene.set_show_roads(on)

    def _on_toggle_show_all_objects(self, on: bool) -> None:
        for tab in self._tab_for_document.values():
            tab.scene.set_show_all_objects(on)

    def _on_toggle_add_road(self, on: bool) -> None:
        if self._current_view is not None:
            self._current_view.set_road_mode(on)

    def _on_road_failed(self, message: str) -> None:
        _log.info("Add Road tool rejected: %s", message)
        self.statusBar().showMessage(f"Add Road: {message}", 5000)

    def _on_template_changed(self) -> None:
        template = self._workspace.template
        path = self._workspace.path
        name = path.name if path else "Untitled"
        if template is not None:
            self.statusBar().showMessage(
                f"Loaded {name}: {len(template.variants)} variant(s), {len(template.zoneLayouts)} layout(s)",
                4000,
            )
        self._update_variant_label()
        self._update_title()

    def _update_title(self, _dirty: bool | None = None) -> None:
        path = self._workspace.path
        if path is None:
            self.setWindowTitle("HoMM:OE Template Editor")
            return
        suffix = " *" if self._workspace.is_dirty else ""
        self.setWindowTitle(f"HoMM:OE Template Editor — {path.name}{suffix}")

    def _update_variant_label(self, _index: int | None = None) -> None:
        template = self._workspace.template
        if template is None or not template.variants:
            self._variant_label.setText("No template")
            return
        cur = self._workspace.current_variant_index + 1
        total = len(template.variants)
        self._variant_label.setText(f"Variant {cur} of {total}")

    def _not_implemented(self) -> None:
        self.statusBar().showMessage("Not implemented yet", 2500)

    def _show_about(self) -> None:
        author_line = '<h4>Author: Ata "Ignis" Hakçıl</h4></br>'  # noqa: RUF001
        body = (
            "<h3>HoMM:OE Template Editor</h3></br>"
            "<p>Graphical editor for Heroes of Might and Magic: Olden Era random-map templates.</p>"
            f"{author_line}"
            '<a href="https://github.com/ignis-sec/HoMM-OE-Template-Editor">Project Link</a></br>'
            f"<p>Version {VERSION}</p></br>"
            f"{CHANGELOG}"
        )

        dialog = QDialog(self)
        dialog.setWindowTitle("About HoMM:OE Template Editor")
        dialog.resize(720, 560)

        layout = QVBoxLayout(dialog)
        browser = QTextBrowser(dialog)
        browser.setOpenExternalLinks(True)
        browser.setHtml(body)
        layout.addWidget(browser, stretch=1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, parent=dialog)
        buttons.rejected.connect(dialog.reject)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)

        dialog.exec()


class _DocumentTab(QWidget):
    def __init__(self, document: Document, catalog: GameDataCatalog) -> None:
        super().__init__()
        self.document = document
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._variant_tabs = VariantTabBar(document.session)
        self._scene = GraphScene(document.session, catalog)
        self._view = GraphView(self._scene)
        layout.addWidget(self._variant_tabs)
        layout.addWidget(self._view, stretch=1)

    @property
    def view(self) -> GraphView:
        return self._view

    @property
    def scene(self) -> GraphScene:
        return self._scene
