"""Icon registry — central lookup for qtawesome-backed icons used across the UI."""

from PySide6.QtGui import QIcon


class IconRegistry:
    def get(self, name: str) -> QIcon:
        raise NotImplementedError
