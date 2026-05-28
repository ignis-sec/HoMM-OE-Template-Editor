"""LogWindow — a non-modal dialog that surfaces the in-memory log buffer.

Lets the user see what would otherwise be invisible inside a `--windowed`
PyInstaller build: logging records, plain print() output, and the formatted
traceback of any uncaught exception captured by the global excepthook.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from templategen.infra.logging import LogBuffer, get_log_buffer


class LogWindow(QDialog):
    _line_received = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Log")
        self.resize(900, 480)
        # Non-modal so the user can keep working while watching the log.
        self.setWindowFlag(Qt.WindowType.WindowMinMaxButtonsHint, True)
        self.setWindowModality(Qt.WindowModality.NonModal)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        self._view = QPlainTextEdit()
        self._view.setReadOnly(True)
        font = QFont("Monospace")
        font.setStyleHint(QFont.StyleHint.TypeWriter)
        self._view.setFont(font)
        self._view.setMaximumBlockCount(0)
        layout.addWidget(self._view, stretch=1)

        bar = QHBoxLayout()
        bar.setSpacing(6)
        self._btn_clear = QPushButton("Clear")
        self._btn_copy = QPushButton("Copy All")
        self._btn_save = QPushButton("Save to file…")
        self._btn_close = QPushButton("Close")
        bar.addWidget(self._btn_clear)
        bar.addWidget(self._btn_copy)
        bar.addWidget(self._btn_save)
        bar.addStretch()
        bar.addWidget(self._btn_close)
        layout.addLayout(bar)

        self._btn_clear.clicked.connect(self._on_clear)
        self._btn_copy.clicked.connect(self._on_copy)
        self._btn_save.clicked.connect(self._on_save)
        self._btn_close.clicked.connect(self.close)

        self._buffer: LogBuffer = get_log_buffer()
        for line in self._buffer.snapshot():
            self._view.appendPlainText(line)
        # The signal hop ensures we re-enter the main thread before touching the
        # widget, since log records can arrive from any thread.
        self._line_received.connect(self._append, Qt.ConnectionType.QueuedConnection)
        self._buffer.add_listener(self._on_buffer_line)

    def _on_buffer_line(self, line: str) -> None:
        # Called from whichever thread emitted the log record.
        self._line_received.emit(line)

    def _append(self, line: str) -> None:
        self._view.appendPlainText(line)

    def _on_clear(self) -> None:
        self._buffer.clear()
        self._view.clear()

    def _on_copy(self) -> None:
        text = self._view.toPlainText()
        if not text:
            return
        QGuiApplication.clipboard().setText(text)

    def _on_save(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save log", "templategen.log", "Log files (*.log);;All files (*)"
        )
        if not path:
            return
        try:
            from pathlib import Path as _Path

            _Path(path).write_text(self._view.toPlainText(), encoding="utf-8")
        except OSError as exc:
            QMessageBox.warning(self, "Save failed", f"Could not write log file:\n{exc}")

    def closeEvent(self, event: object) -> None:
        self._buffer.remove_listener(self._on_buffer_line)
        super().closeEvent(event)
