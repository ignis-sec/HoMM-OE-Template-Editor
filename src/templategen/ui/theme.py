"""Apply the application's visual theme."""

import qdarktheme
from PySide6.QtWidgets import QApplication


def apply_theme(app: QApplication, mode: str = "dark") -> None:
    qdarktheme.setup_theme(mode)
    app.setStyle("Fusion")
