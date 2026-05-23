"""Application entry point."""

import sys

from PySide6.QtWidgets import QApplication

from templategen import __version__
from templategen.catalog.game_data import GameDataCatalog
from templategen.infra.logging import configure_logging
from templategen.services.clipboard import EditorClipboard
from templategen.services.workspace import Workspace
from templategen.ui.dialogs.first_run import run_first_time_setup_if_needed
from templategen.ui.icons import IconRegistry
from templategen.ui.main_window import MainWindow
from templategen.ui.theme import apply_theme


def main() -> int:
    configure_logging()

    app = QApplication(sys.argv)
    app.setApplicationName("HoMM:OE Template Editor")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("templategen")

    apply_theme(app)

    run_first_time_setup_if_needed()

    clipboard = EditorClipboard()
    workspace = Workspace(clipboard)
    icons = IconRegistry()
    catalog = GameDataCatalog()
    window = MainWindow(workspace, icons, catalog, clipboard)
    window.show()

    return app.exec()
