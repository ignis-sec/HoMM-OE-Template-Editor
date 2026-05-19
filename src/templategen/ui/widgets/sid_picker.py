"""Autocompleting picker for object SIDs, backed by the ReferenceCatalog."""

from PySide6.QtWidgets import QWidget

from templategen.catalog.catalog import ReferenceCatalog


class SidPicker(QWidget):
    def __init__(self, catalog: ReferenceCatalog) -> None:
        super().__init__()
        self._catalog = catalog
