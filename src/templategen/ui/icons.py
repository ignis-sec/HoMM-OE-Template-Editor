"""Icon registry — semantic icon names mapped to qtawesome glyphs."""

from typing import Final

import qtawesome as qta
from PySide6.QtGui import QIcon

_ICON_MAP: Final[dict[str, str]] = {
    "new": "fa5s.file-medical",
    "open": "fa5s.folder-open",
    "save": "fa5s.save",
    "save_as": "fa5s.file-export",
    "exit": "fa5s.sign-out-alt",
    "undo": "fa5s.undo",
    "redo": "fa5s.redo",
    "validate": "fa5s.check-circle",
    "add_variant": "fa5s.plus-square",
    "remove_variant": "fa5s.minus-square",
    "add_zone": "fa5s.plus-circle",
    "connect": "fa5s.link",
    "delete": "fa5s.trash",
    "settings": "fa5s.cog",
    "library": "fa5s.book",
    "inspector": "fa5s.sliders-h",
    "about": "fa5s.info-circle",
    "roads": "fa5s.road",
    "show_all_objects": "fa5s.eye",
    "add_road": "fa5s.route",
    "reset_road_layout": "fa5s.magic",
}


class IconRegistry:
    def get(self, name: str) -> QIcon:
        return qta.icon(_ICON_MAP[name])
