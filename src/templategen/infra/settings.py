"""Persistent user settings wrapper around QSettings."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class AppSettings:
    @property
    def recent_files(self) -> list[Path]:
        raise NotImplementedError

    def remember_recent(self, path: Path) -> None:
        raise NotImplementedError

    @property
    def window_geometry(self) -> bytes | None:
        raise NotImplementedError

    @window_geometry.setter
    def window_geometry(self, value: bytes) -> None:
        raise NotImplementedError
