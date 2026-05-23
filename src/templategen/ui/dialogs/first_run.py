"""First-run flow: detect or locate the game install, then build the catalog."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMessageBox,
    QProgressDialog,
    QWidget,
)

from templategen.catalog.builder import build_snapshot, write_snapshot
from templategen.infra.paths import (
    app_data_root,
    catalog_json_path,
    extracted_core_dir,
    item_icons_dir,
    spell_icons_dir,
)
from templategen.services.game_assets import (
    extract_core_zip,
    extract_named_textures,
    find_game_install,
    is_game_install,
)

_log = logging.getLogger(__name__)
_WARNING = (
    "If you select no, you won't have item, spell and interactable thumbnails, "
    "and you might not be able to see id dropdown options correctly."
)


def run_first_time_setup_if_needed(parent: QWidget | None = None) -> None:
    """If no catalog is present in AppLocalDataLocation, walk the user through building one."""
    if catalog_json_path().is_file():
        return
    _interactive_build(parent)


def rebuild_catalog_interactive(parent: QWidget | None = None) -> bool:
    """Force-rebuild the catalog. Returns True if a build actually ran."""
    return _interactive_build(parent)


def _interactive_build(parent: QWidget | None) -> bool:
    detected = find_game_install()
    if detected is not None:
        if not _prompt_use_found(detected, parent):
            return False
        _build_with_progress(detected, parent)
        return True

    if not _prompt_locate(parent):
        return False
    chosen = _ask_for_install_dir(parent)
    if chosen is None:
        return False
    _build_with_progress(chosen, parent)
    return True


def _prompt_use_found(game_path: Path, parent: QWidget | None) -> bool:
    box = QMessageBox(parent)
    box.setWindowTitle("Game install found")
    box.setIcon(QMessageBox.Icon.Question)
    box.setText(
        "Game directory found, build template, item and thumbnail catalog from game files?"
    )
    box.setInformativeText(f"<i>{_WARNING}</i><br><br>Game directory:<br><code>{game_path}</code>")
    box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    box.setDefaultButton(QMessageBox.StandardButton.Yes)
    return box.exec() == QMessageBox.StandardButton.Yes


def _prompt_locate(parent: QWidget | None) -> bool:
    box = QMessageBox(parent)
    box.setWindowTitle("Game install not found")
    box.setIcon(QMessageBox.Icon.Question)
    box.setText("Game directory not found, locate the game?")
    box.setInformativeText(f"<i>{_WARNING}</i>")
    box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    box.setDefaultButton(QMessageBox.StandardButton.Yes)
    return box.exec() == QMessageBox.StandardButton.Yes


def _ask_for_install_dir(parent: QWidget | None) -> Path | None:
    while True:
        chosen = QFileDialog.getExistingDirectory(
            parent,
            "Locate your Heroes of Might & Magic Olden Era install folder",
            str(Path.home()),
        )
        if not chosen:
            return None
        path = Path(chosen)
        if is_game_install(path):
            return path
        retry = QMessageBox.question(
            parent,
            "Not a game install",
            (
                "The folder does not look like a valid game install "
                "(no HeroesOldenEra_Data/app.info found).\n\n"
                f"{path}\n\nTry again?"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if retry != QMessageBox.StandardButton.Yes:
            return None


def _build_with_progress(game_install: Path, parent: QWidget | None) -> None:
    progress = QProgressDialog("Preparing…", "Cancel", 0, 100, parent)
    progress.setWindowTitle("Building catalog")
    progress.setWindowModality(Qt.WindowModality.WindowModal)
    progress.setMinimumDuration(0)
    progress.setAutoClose(False)
    progress.setAutoReset(False)
    progress.setValue(0)

    worker = _BuildWorker(game_install)

    def on_step(percent: int, message: str) -> None:
        progress.setValue(percent)
        progress.setLabelText(message)
        QApplication.processEvents()

    worker.step.connect(on_step)
    worker.finished.connect(progress.close)

    worker.start()
    while worker.isRunning():
        QApplication.processEvents()
        if progress.wasCanceled():
            worker.requestInterruption()
            worker.wait(2000)
            break
        worker.wait(50)

    progress.close()

    if worker.error is not None:
        QMessageBox.critical(
            parent,
            "Catalog build failed",
            f"Building the catalog failed:\n\n{worker.error}",
        )


def _icon_names_from(payloads: dict) -> list[str]:
    out: list[str] = []
    for payload in payloads.values():
        if not isinstance(payload, dict):
            continue
        icon = payload.get("icon")
        if isinstance(icon, str):
            out.append(icon)
    return out


class _BuildWorker(QThread):
    step = Signal(int, str)

    def __init__(self, game_install: Path) -> None:
        super().__init__()
        self._game_install = game_install
        self.error: str | None = None

    def run(self) -> None:
        try:
            app_data_root()  # ensure root exists

            self.step.emit(5, "Extracting Core.zip from game install…")
            core_root = extract_core_zip(self._game_install, extracted_core_dir())

            self.step.emit(35, "Building reference catalog…")
            snapshot = build_snapshot(core_root)
            write_snapshot(snapshot, catalog_json_path())

            artifact_icons = _icon_names_from(snapshot.get("artifacts", {}))
            spell_icons = _icon_names_from(snapshot.get("spells", {}))

            self.step.emit(55, "Extracting artifact icons from game assets…")
            saved_a, missing_a = extract_named_textures(
                self._game_install,
                artifact_icons,
                item_icons_dir(),
                kind="artifact icons",
                progress=lambda done, total: self.step.emit(
                    55 + int(20 * done / max(total, 1)),
                    f"Extracting artifact icons ({done}/{total})…",
                ),
            )

            self.step.emit(75, "Extracting spell icons from game assets…")
            saved_s, missing_s = extract_named_textures(
                self._game_install,
                spell_icons,
                spell_icons_dir(),
                kind="spell icons",
                progress=lambda done, total: self.step.emit(
                    75 + int(20 * done / max(total, 1)),
                    f"Extracting spell icons ({done}/{total})…",
                ),
            )

            self.step.emit(98, "Finishing…")
            _log.info(
                "first-run build: %d artifacts (%d icons, %d missing), %d spells (%d icons, %d missing)",
                len(artifact_icons), saved_a, len(missing_a),
                len(spell_icons), saved_s, len(missing_s),
            )
            self.step.emit(100, "Done")
        except Exception as exc:
            self.error = f"{type(exc).__name__}: {exc}"
            _log.exception("first-run build failed")
