"""Application entry point."""

import sys

from PySide6.QtWidgets import QApplication

from templategen import __version__
from templategen.catalog.game_data import GameDataCatalog
from templategen.infra.logging import configure_logging
from templategen.services.session import EditorSession
from templategen.ui.icons import IconRegistry
from templategen.ui.main_window import MainWindow
from templategen.ui.theme import apply_theme


def main() -> int:
    configure_logging()

    app = QApplication(sys.argv)
    app.setApplicationName("TemplateGenerator")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("templategen")

    apply_theme(app)

    session = EditorSession()
    icons = IconRegistry()
    catalog = GameDataCatalog()
    window = MainWindow(session, icons, catalog)
    window.show()

    return app.exec()
