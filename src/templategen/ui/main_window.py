"""Main application window — wires menus, toolbar, docks, and status bar."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
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

from templategen.services.session import EditorSession
from templategen.ui.canvas.graph_scene import GraphScene
from templategen.ui.canvas.graph_view import GraphView
from templategen.ui.icons import IconRegistry
from templategen.ui.panels.inspector import Inspector
from templategen.ui.panels.library import LibraryPanel
from templategen.ui.panels.variant_tabs import VariantTabBar


class MainWindow(QMainWindow):
    def __init__(self, session: EditorSession, icons: IconRegistry) -> None:
        super().__init__()
        self._session = session
        self._icons = icons

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

    def _build_actions(self) -> None:
        self.action_new = QAction(self._icons.get("new"), "&New Template", self)
        self.action_new.setShortcut(QKeySequence.StandardKey.New)
        self.action_new.triggered.connect(self._not_implemented)

        self.action_open = QAction(self._icons.get("open"), "&Open…", self)
        self.action_open.setShortcut(QKeySequence.StandardKey.Open)
        self.action_open.triggered.connect(self._on_open)

        self.action_save = QAction(self._icons.get("save"), "&Save", self)
        self.action_save.setShortcut(QKeySequence.StandardKey.Save)
        self.action_save.triggered.connect(self._not_implemented)

        self.action_save_as = QAction(self._icons.get("save_as"), "Save &As…", self)
        self.action_save_as.setShortcut(QKeySequence.StandardKey.SaveAs)
        self.action_save_as.triggered.connect(self._not_implemented)

        self.action_exit = QAction(self._icons.get("exit"), "E&xit", self)
        self.action_exit.setShortcut(QKeySequence.StandardKey.Quit)
        self.action_exit.triggered.connect(self.close)

        self.action_undo = QAction(self._icons.get("undo"), "&Undo", self)
        self.action_undo.setShortcut(QKeySequence.StandardKey.Undo)
        self.action_undo.triggered.connect(self._not_implemented)

        self.action_redo = QAction(self._icons.get("redo"), "&Redo", self)
        self.action_redo.setShortcut(QKeySequence.StandardKey.Redo)
        self.action_redo.triggered.connect(self._not_implemented)

        self.action_add_variant = QAction(self._icons.get("add_variant"), "&Add Variant", self)
        self.action_add_variant.triggered.connect(self._not_implemented)

        self.action_remove_variant = QAction(self._icons.get("remove_variant"), "&Remove Current Variant", self)
        self.action_remove_variant.triggered.connect(self._not_implemented)

        self.action_validate = QAction(self._icons.get("validate"), "&Validate", self)
        self.action_validate.setShortcut("F5")
        self.action_validate.triggered.connect(self._not_implemented)

        self.action_template_settings = QAction(self._icons.get("settings"), "Template &Settings…", self)
        self.action_template_settings.triggered.connect(self._not_implemented)

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
            Inspector(self._session),
            Qt.DockWidgetArea.RightDockWidgetArea,
        )

        self.menu_view.addAction(self._library_dock.toggleViewAction())
        self.menu_view.addAction(self._inspector_dock.toggleViewAction())

    def _make_dock(self, title: str, content: QWidget, area: Qt.DockWidgetArea) -> QDockWidget:
        dock = QDockWidget(title, self)
        dock.setWidget(content)
        dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.addDockWidget(area, dock)
        return dock

    def _build_statusbar(self) -> None:
        bar = self.statusBar()
        bar.showMessage("Ready")
        self._variant_label = QLabel("No template")
        bar.addPermanentWidget(self._variant_label)

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
            self._session.load(Path(path))
        except Exception as exc:
            QMessageBox.critical(self, "Open failed", f"Could not load template:\n\n{exc}")

    def _on_template_changed(self) -> None:
        template = self._session.template
        path = self._session.path
        name = path.name if path else "Untitled"
        self.setWindowTitle(f"TemplateGenerator — {name}")
        if template is not None:
            self.statusBar().showMessage(
                f"Loaded {name}: {len(template.variants)} variant(s), "
                f"{len(template.zoneLayouts)} layout(s)",
                4000,
            )
        self._update_variant_label()

    def _update_variant_label(self, _index: int | None = None) -> None:
        template = self._session.template
        if template is None or not template.variants:
            self._variant_label.setText("No template")
            return
        cur = self._session.current_variant_index + 1
        total = len(template.variants)
        self._variant_label.setText(f"Variant {cur} of {total}")

    def _not_implemented(self) -> None:
        self.statusBar().showMessage("Not implemented yet", 2500)

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "About TemplateGenerator",
            "<h3>TemplateGenerator</h3>"
            "<p>Graphical editor for Heroes of Might and Magic: Olden Era random-map templates.</p>",
        )
