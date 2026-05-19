"""Application entry point."""

import sys

from PySide6.QtWidgets import QApplication

from templategen import __version__
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
    window = MainWindow(session, icons)
    window.show()

    return app.exec()
