"""Validation results dialog — shows a list of ValidationIssue with severity icons."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from templategen.services.validator import Severity

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from templategen.services.validator import ValidationIssue


_SEVERITY_PREFIX = {
    Severity.ERROR: "[ERROR]",
    Severity.WARNING: "[WARN] ",
    Severity.INFO: "[INFO] ",
}


class ValidationResultsDialog(QDialog):
    def __init__(
        self,
        issues: Sequence[ValidationIssue],
        on_select: Callable[[object], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Validation results")
        self.resize(640, 420)
        self._on_select = on_select

        layout = QVBoxLayout(self)
        if not issues:
            label = QLabel("No issues found.")
            label.setStyleSheet("color: #4caf50; padding: 12px;")
            layout.addWidget(label)
        else:
            errors = sum(1 for i in issues if i.severity == Severity.ERROR)
            warnings = sum(1 for i in issues if i.severity == Severity.WARNING)
            summary = QLabel(f"{len(issues)} issue(s) — {errors} error(s), {warnings} warning(s)")
            layout.addWidget(summary)

            self._list = QListWidget()
            for issue in issues:
                prefix = _SEVERITY_PREFIX.get(issue.severity, "")
                widget_item = QListWidgetItem(f"{prefix} {issue.message}")
                widget_item.setData(Qt.ItemDataRole.UserRole, issue.target)
                self._list.addItem(widget_item)
            self._list.itemActivated.connect(self._on_activated)
            layout.addWidget(self._list, stretch=1)

            hint = QLabel("Double-click an issue to select its target in the editor.")
            hint.setStyleSheet("color: #888;")
            layout.addWidget(hint)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    def _on_activated(self, item: QListWidgetItem) -> None:
        target = item.data(Qt.ItemDataRole.UserRole)
        if target is not None:
            self._on_select(target)
