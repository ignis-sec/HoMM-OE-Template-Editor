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
    fraction_icons_dir,
    interactable_icons_dir,
    item_icons_dir,
    resource_icons_dir,
    spell_icons_dir,
)
from templategen.services.game_assets import (
    extract_core_zip,
    extract_named_textures,
    find_game_install,
    is_game_install,
    remember_game_install,
    saved_game_install,
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
    """Force-rebuild the catalog. Skips the chooser when a previously-confirmed install
    path is still valid. Returns True if a build actually ran."""
    remembered = saved_game_install()
    if remembered is not None:
        return _build_with_progress(remembered, parent)
    return _interactive_build(parent)


def _interactive_build(parent: QWidget | None) -> bool:
    detected = saved_game_install() or find_game_install()
    if detected is not None:
        if not _prompt_use_found(detected, parent):
            return False
        if not _build_with_progress(detected, parent):
            return False
        remember_game_install(detected)
        return True

    if not _prompt_locate(parent):
        return False
    chosen = _ask_for_install_dir(parent)
    if chosen is None:
        return False
    if not _build_with_progress(chosen, parent):
        return False
    remember_game_install(chosen)
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


def _build_with_progress(game_install: Path, parent: QWidget | None) -> bool:
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
        return False
    return True


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
            interactable_icons = _icon_names_from(snapshot.get("interactables", {}))
            resource_icons = _icon_names_from(snapshot.get("resources", {}))

            self.step.emit(50, "Extracting artifact icons from game assets…")
            saved_a, missing_a = extract_named_textures(
                self._game_install,
                artifact_icons,
                item_icons_dir(),
                kind="artifact icons",
                progress=lambda done, total: self.step.emit(
                    50 + int(15 * done / max(total, 1)),
                    f"Extracting artifact icons ({done}/{total})…",
                ),
            )

            self.step.emit(65, "Extracting spell icons from game assets…")
            saved_s, missing_s = extract_named_textures(
                self._game_install,
                spell_icons,
                spell_icons_dir(),
                kind="spell icons",
                progress=lambda done, total: self.step.emit(
                    65 + int(15 * done / max(total, 1)),
                    f"Extracting spell icons ({done}/{total})…",
                ),
            )

            self.step.emit(80, "Extracting map-object icons from game assets…")
            saved_i, missing_i = extract_named_textures(
                self._game_install,
                interactable_icons,
                interactable_icons_dir(),
                kind="interactable icons",
                prefer_size=(64, 64),
                progress=lambda done, total: self.step.emit(
                    80 + int(10 * done / max(total, 1)),
                    f"Extracting map-object icons ({done}/{total})…",
                ),
            )

            self.step.emit(88, "Extracting resource icons from game assets…")
            saved_r, missing_r = extract_named_textures(
                self._game_install,
                resource_icons,
                resource_icons_dir(),
                kind="resource icons",
                prefer_size=(64, 64),
                progress=lambda done, total: self.step.emit(
                    88 + int(5 * done / max(total, 1)),
                    f"Extracting resource icons ({done}/{total})…",
                ),
            )

            self.step.emit(94, "Extracting faction icons from game assets…")
            fraction_names = [f"fraction_{f}" for f in snapshot.get("fractions", [])]
            saved_f, missing_f = extract_named_textures(
                self._game_install,
                fraction_names,
                fraction_icons_dir(),
                kind="faction icons",
            )

            self.step.emit(98, "Finishing…")
            _log.info(
                "first-run build: %d/%d artifacts, %d/%d spells, %d/%d interactables, %d/%d resources, %d/%d fractions",
                saved_a, len(artifact_icons),
                saved_s, len(spell_icons),
                saved_i, len(interactable_icons),
                saved_r, len(resource_icons),
                saved_f, len(fraction_names),
            )
            if missing_a or missing_s or missing_i or missing_r or missing_f:
                _log.info(
                    "missing icon assets — artifacts: %s, spells: %s, interactables: %s, resources: %s, fractions: %s",
                    missing_a[:5], missing_s[:5], missing_i[:5], missing_r[:5], missing_f[:5],
                )
            self.step.emit(100, "Done")
        except Exception as exc:
            self.error = f"{type(exc).__name__}: {exc}"
            _log.exception("first-run build failed")
