"""Application-wide logging setup.

Adds an in-memory ring buffer that the GUI's "Log Window" tab can read from,
plus stdout/stderr tee-ing and an excepthook so unhandled tracebacks end up
visible inside the packaged Windows executable (where the underlying console
is detached and `print` writes to nowhere).
"""

from __future__ import annotations

import contextlib
import logging
import sys
import threading
import traceback
from collections import deque
from typing import TYPE_CHECKING, TextIO

if TYPE_CHECKING:
    from collections.abc import Callable

_LINE_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"
_DATE_FORMAT = "%H:%M:%S"
_BUFFER_CAPACITY = 10_000


class LogBuffer:
    """Thread-safe ring buffer of formatted log lines + listener callbacks."""

    def __init__(self, capacity: int = _BUFFER_CAPACITY) -> None:
        self._lines: deque[str] = deque(maxlen=capacity)
        self._listeners: list[Callable[[str], None]] = []
        self._lock = threading.Lock()

    def append(self, line: str) -> None:
        line = line.rstrip("\n")
        if not line:
            return
        with self._lock:
            self._lines.append(line)
            listeners = list(self._listeners)
        # A misbehaving listener must never be allowed to take down the logging
        # path, since we may be inside the global excepthook here.
        for cb in listeners:
            with contextlib.suppress(Exception):
                cb(line)

    def snapshot(self) -> list[str]:
        with self._lock:
            return list(self._lines)

    def clear(self) -> None:
        with self._lock:
            self._lines.clear()

    def add_listener(self, callback: Callable[[str], None]) -> None:
        with self._lock:
            self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[str], None]) -> None:
        with self._lock:
            if callback in self._listeners:
                self._listeners.remove(callback)


class _BufferHandler(logging.Handler):
    def __init__(self, buffer: LogBuffer) -> None:
        super().__init__()
        self._buffer = buffer

    def emit(self, record: logging.LogRecord) -> None:
        try:
            line = self.format(record)
        except Exception:
            return
        self._buffer.append(line)


class _TeeStream:
    """File-like wrapper that mirrors writes to the original stream AND a log buffer."""

    def __init__(self, original: TextIO, buffer: LogBuffer, label: str) -> None:
        self._original = original
        self._buffer = buffer
        self._label = label
        self._pending = ""

    def write(self, data: str) -> int:
        with contextlib.suppress(Exception):
            self._original.write(data)
        # Coalesce partial writes into whole lines so the log window doesn't
        # show every chunk on its own row.
        self._pending += data
        while "\n" in self._pending:
            line, _, self._pending = self._pending.partition("\n")
            self._buffer.append(f"[{self._label}] {line}")
        return len(data)

    def flush(self) -> None:
        with contextlib.suppress(Exception):
            self._original.flush()
        if self._pending:
            self._buffer.append(f"[{self._label}] {self._pending}")
            self._pending = ""

    def __getattr__(self, name: str) -> object:
        return getattr(self._original, name)


_log_buffer: LogBuffer | None = None
_configured: bool = False


def get_log_buffer() -> LogBuffer:
    global _log_buffer
    if _log_buffer is None:
        _log_buffer = LogBuffer()
    return _log_buffer


def configure_logging(level: int = logging.INFO) -> None:
    global _configured
    if _configured:
        return
    _configured = True

    buffer = get_log_buffer()

    handler = _BufferHandler(buffer)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter(_LINE_FORMAT, datefmt=_DATE_FORMAT))

    root = logging.getLogger()
    # Set up the standard console handler too; basicConfig only installs once.
    logging.basicConfig(level=level, format=_LINE_FORMAT, datefmt=_DATE_FORMAT)
    root.setLevel(min(root.level, logging.DEBUG))
    root.addHandler(handler)

    # Tee stdout/stderr so plain print()s and PySide/Qt diagnostics show up.
    sys.stdout = _TeeStream(sys.stdout, buffer, "stdout")
    sys.stderr = _TeeStream(sys.stderr, buffer, "stderr")

    # Surface uncaught exceptions even in `--windowed` builds where stderr is
    # detached. KeyboardInterrupt is left alone so Ctrl+C still exits cleanly.
    def _hook(exc_type: type[BaseException], exc: BaseException, tb: object) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc, tb)
            return
        formatted = "".join(traceback.format_exception(exc_type, exc, tb))
        buffer.append("[uncaught exception]")
        for line in formatted.rstrip().splitlines():
            buffer.append(line)
        logging.getLogger("excepthook").error("uncaught exception", exc_info=(exc_type, exc, tb))

    sys.excepthook = _hook
