"""Application entry point."""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from templategen import __version__
from templategen.catalog.game_data import GameDataCatalog
from templategen.infra.logging import configure_logging
from templategen.services.clipboard import EditorClipboard
from templategen.services.workspace import Workspace
from templategen.ui.icons import IconRegistry
from templategen.ui.main_window import MainWindow
from templategen.ui.theme import apply_theme


def _resolve_catalog_path() -> Path:
    """Locate data/catalog.json — next to the executable for bundles, else cwd-relative."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "data" / "catalog.json"
    return Path("data/catalog.json")


def main() -> int:
    configure_logging()

    app = QApplication(sys.argv)
    app.setApplicationName("HoMM:OE Template Editor")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("templategen")

    apply_theme(app)

    clipboard = EditorClipboard()
    workspace = Workspace(clipboard)
    icons = IconRegistry()
    catalog = GameDataCatalog(snapshot_path=_resolve_catalog_path())
    window = MainWindow(workspace, icons, catalog, clipboard)
    window.show()

    return app.exec()
