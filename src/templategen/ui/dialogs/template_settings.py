"""Template-wide settings dialog — Basic, Game Rules, Win Conditions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from templategen.model.enums import GameMode
from templategen.model.game_rules import Bonus, GlobalBans, ValueOverride, WinConditions
from templategen.services.commands import EditFieldCommand
from templategen.ui.asset_icons import artifact_listables
from templategen.ui.widgets.field_binding import bind_int, bind_string
from templategen.ui.widgets.list_editors import (
    InlineSubObjectListEditor,
    ReferenceListEditor,
    ScalarListEditor,
)
from templategen.ui.widgets.sid_picker import SidPicker

if TYPE_CHECKING:
    from collections.abc import Callable

    from templategen.catalog.game_data import GameDataCatalog
    from templategen.model.template import Template
    from templategen.services.workspace import Workspace


@dataclass
class _Field:
    target: object
    name: str
    read: Callable[[], Any]


class TemplateSettingsDialog(QDialog):
    def __init__(
        self,
        session: Workspace,
        template: Template,
        catalog: GameDataCatalog,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Template Settings")
        self.resize(560, 640)
        self._session = session
        self._template = template
        self._catalog = catalog
        self._fields: list[_Field] = []

        layout = QVBoxLayout(self)
        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

        self._tabs.addTab(self._build_basic_tab(), "Basic")
        self._tabs.addTab(self._build_game_rules_tab(), "Game Rules")
        self._tabs.addTab(self._build_win_conditions_tab(), "Win Conditions")
        self._tabs.addTab(self._build_bans_tab(), "Global Bans")
        self._tabs.addTab(self._build_bonuses_tab(), "Bonuses")
        self._tabs.addTab(self._build_value_overrides_tab(), "Value Overrides")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _build_basic_tab(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)

        form.addRow("Name:", self._track_line(self._template, "name", placeholder=""))
        form.addRow("Description:", self._track_line(self._template, "description", placeholder=""))
        form.addRow("Display win condition:", self._track_line(self._template, "displayWinCondition", placeholder=""))
        form.addRow("Game mode:", self._track_enum(self._template, "gameMode", GameMode))
        form.addRow("Size X:", self._track_int(self._template, "sizeX", 16, 4096, step=16))
        form.addRow("Size Z:", self._track_int(self._template, "sizeZ", 16, 4096, step=16))

        return widget

    def _build_game_rules_tab(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)
        rules = self._template.gameRules

        form.addRow("Hero count min:", self._track_int(rules, "heroCountMin", 0, 32))
        form.addRow("Hero count max:", self._track_int(rules, "heroCountMax", 0, 32))
        form.addRow("Hero count increment:", self._track_int(rules, "heroCountIncrement", 0, 32))
        form.addRow("Hero hire ban:", self._track_bool(rules, "heroHireBan"))
        form.addRow("Encounter holes:", self._track_bool(rules, "encounterHoles"))
        form.addRow("Faction laws exp modifier:", self._track_float(rules, "factionLawsExpModifier", 0.0, 10.0, 0.05))
        form.addRow("Astrology exp modifier:", self._track_float(rules, "astrologyExpModifier", 0.0, 10.0, 0.05))
        form.addRow("Champion select rule:", self._track_line(rules, "championSelectRule", placeholder=""))

        return widget

    def _build_win_conditions_tab(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)
        wc = self._template.gameRules.winConditions or WinConditions()
        if self._template.gameRules.winConditions is None:
            self._template.gameRules.winConditions = wc

        form.addRow("Classic:", self._track_bool(wc, "classic"))
        form.addRow("Desertion:", self._track_bool(wc, "desertion"))
        form.addRow("Desertion day:", self._track_int(wc, "desertionDay", 0, 999))
        form.addRow("Desertion value:", self._track_int(wc, "desertionValue", 0, 1_000_000))
        form.addRow("Hero lighting:", self._track_bool(wc, "heroLighting"))
        form.addRow("Hero lighting day:", self._track_int(wc, "heroLightingDay", 0, 999))
        form.addRow("Lost start city:", self._track_bool(wc, "lostStartCity"))
        form.addRow("Lost start city day:", self._track_int(wc, "lostStartCityDay", 0, 999))
        form.addRow("Lost start hero:", self._track_bool(wc, "lostStartHero"))
        form.addRow("City hold:", self._track_bool(wc, "cityHold"))
        form.addRow("City hold days:", self._track_int(wc, "cityHoldDays", 0, 999))
        form.addRow("Hold city win con:", self._track_bool(wc, "holdCityWinCon"))
        form.addRow("Encounter holes:", self._track_bool(wc, "encounterHoles"))

        form.addRow("Gladiator arena:", self._track_bool(wc, "gladiatorArena"))
        form.addRow("Gladiator: start on work:", self._track_bool(wc, "gladiatorArenaRegistrationStartWork"))
        form.addRow("Gladiator: start on fight:", self._track_bool(wc, "gladiatorArenaRegistrationStartFight"))
        form.addRow("Gladiator delay start:", self._track_int(wc, "gladiatorArenaDaysDelayStart", 0, 999))
        form.addRow("Gladiator count day:", self._track_int(wc, "gladiatorArenaCountDay", 0, 999))
        form.addRow("Champion select rule:", self._track_line(wc, "championSelectRule", placeholder=""))

        form.addRow("Tournament:", self._track_bool(wc, "tournament"))
        form.addRow("Tournament save army:", self._track_bool(wc, "tournamentSaveArmy"))
        form.addRow("Tournament points to win:", self._track_int(wc, "tournamentPointsToWin", 0, 1_000_000))

        return widget

    def _build_bans_tab(self) -> QWidget:
        return _BansTab(self._session, self._template, self._catalog)

    def _build_bonuses_tab(self) -> QWidget:
        return _BonusesTab(self._session, self._template, self._catalog)

    def _build_value_overrides_tab(self) -> QWidget:
        return _ValueOverridesTab(self._session, self._template, self._catalog)

    def _on_accept(self) -> None:
        changes: list[tuple[object, str, Any]] = []
        for field in self._fields:
            new_value = field.read()
            old_value = getattr(field.target, field.name)
            if new_value != old_value:
                changes.append((field.target, field.name, new_value))

        if changes:
            self._session.begin_macro("Edit template settings")
            try:
                for target, name, value in changes:
                    self._session.execute(EditFieldCommand(self._session, target, name, value))
            finally:
                self._session.end_macro()

        self.accept()

    def _track_line(self, target: object, name: str, *, placeholder: str = "") -> QLineEdit:
        widget = QLineEdit()
        current = getattr(target, name)
        widget.setText("" if current is None else str(current))
        widget.setPlaceholderText(placeholder)
        self._fields.append(_Field(target, name, lambda: widget.text() or None))
        return widget

    def _track_int(
        self,
        target: object,
        name: str,
        minimum: int,
        maximum: int,
        *,
        step: int = 1,
    ) -> QSpinBox:
        widget = QSpinBox()
        widget.setRange(minimum, maximum)
        widget.setSingleStep(step)
        current = getattr(target, name)
        widget.setValue(int(current) if current is not None else 0)
        self._fields.append(_Field(target, name, widget.value))
        return widget

    def _track_float(
        self,
        target: object,
        name: str,
        minimum: float,
        maximum: float,
        step: float,
    ) -> QDoubleSpinBox:
        widget = QDoubleSpinBox()
        widget.setRange(minimum, maximum)
        widget.setSingleStep(step)
        widget.setDecimals(3)
        current = getattr(target, name)
        widget.setValue(float(current) if current is not None else 0.0)
        self._fields.append(_Field(target, name, widget.value))
        return widget

    def _track_bool(self, target: object, name: str) -> QCheckBox:
        widget = QCheckBox()
        widget.setChecked(bool(getattr(target, name) or False))
        self._fields.append(_Field(target, name, widget.isChecked))
        return widget

    def _track_enum(self, target: object, name: str, enum_type: type) -> QComboBox:
        widget = QComboBox()
        values = list(enum_type)
        widget.addItems([v.value for v in values])
        current = getattr(target, name)
        if current is not None:
            idx = widget.findText(current.value if hasattr(current, "value") else str(current))
            if idx >= 0:
                widget.setCurrentIndex(idx)

        def read() -> Any:
            text = widget.currentText()
            return next((v for v in values if v.value == text), None)

        self._fields.append(_Field(target, name, read))
        return widget

class _BansTab(QWidget):
    def __init__(self, session: Workspace, template: Template, catalog: GameDataCatalog) -> None:
        super().__init__()
        self._session = session
        self._template = template
        self._catalog = catalog
        self._layout = QVBoxLayout(self)
        self._rebuild()
        session.model_object_changed.connect(self._on_model_changed)

    def _on_model_changed(self, obj: object) -> None:
        if obj is self._template:
            self._rebuild()

    def _rebuild(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.deleteLater()

        if self._template.globalBans is None:
            hint = QLabel("This template has no global bans defined.")
            hint.setStyleSheet("color: #888;")
            self._layout.addWidget(hint)
            enable = QPushButton("Enable global bans")
            enable.clicked.connect(self._initialize)
            self._layout.addWidget(enable, alignment=self._layout.alignment())
            self._layout.addStretch()
            return

        bans = self._template.globalBans
        spell_choices = lambda: list(self._catalog.known_spell_sids())  # noqa: E731
        artifact_choices = lambda: artifact_listables(self._catalog)  # noqa: E731
        self._layout.addWidget(QLabel("Banned magics:"))
        self._layout.addWidget(ReferenceListEditor(bans, "magics", self._session, choices=spell_choices))
        self._layout.addWidget(QLabel("Banned items:"))
        self._layout.addWidget(ReferenceListEditor(bans, "items", self._session, choices=artifact_choices))
        self._layout.addStretch()

    def _initialize(self) -> None:
        self._session.execute(
            EditFieldCommand(self._session, self._template, "globalBans", GlobalBans())
        )


def _populate_bonus_row(
    form: QFormLayout,
    bonus: Bonus,
    refreshers: list[Any],
    session: Workspace,
    catalog: GameDataCatalog,
) -> None:
    sid = SidPicker(bonus, "sid", session, choices=catalog.known_bonus_sids)
    refreshers.append(sid.refresh)
    form.addRow("Sid:", sid)

    side = QSpinBox()
    side.setRange(-1, 32)
    refreshers.append(bind_int(side, bonus, "receiverSide", session))
    form.addRow("Receiver side:", side)

    filt = QLineEdit()
    refreshers.append(bind_string(filt, bonus, "receiverFilter", session, optional=True))
    form.addRow("Receiver filter:", filt)

    params = ScalarListEditor(bonus, "parameters", session)
    refreshers.append(params.refresh)
    form.addRow("Parameters:", params)


def _populate_value_override_row(
    form: QFormLayout,
    override: ValueOverride,
    refreshers: list[Any],
    session: Workspace,
    catalog: GameDataCatalog,
) -> None:
    sid = SidPicker(override, "sid", session, choices=catalog.known_sids)
    refreshers.append(sid.refresh)
    form.addRow("Sid:", sid)

    variant = QSpinBox()
    variant.setRange(-1, 100_000)
    refreshers.append(bind_int(variant, override, "variant", session))
    form.addRow("Variant:", variant)

    guard = QSpinBox()
    guard.setRange(0, 1_000_000_000)
    guard.setSingleStep(1000)
    refreshers.append(bind_int(guard, override, "guardValue", session))
    form.addRow("Guard value:", guard)


class _BonusesTab(QWidget):
    def __init__(self, session: Workspace, template: Template, catalog: GameDataCatalog) -> None:
        super().__init__()
        self._session = session
        self._template = template
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        if not isinstance(template.gameRules.bonuses, list):
            existing = template.gameRules.bonuses
            template.gameRules.bonuses = [existing] if isinstance(existing, Bonus) else []

        editor = InlineSubObjectListEditor(
            template.gameRules,
            "bonuses",
            session,
            factories=[("Bonus", lambda: Bonus(sid="new_bonus"))],
            populate=lambda form, obj, refs: _populate_bonus_row(form, obj, refs, session, catalog),
            title_for_item=lambda obj, idx: f"Bonus [{idx}]: {obj.sid or '(unnamed)'}",
        )
        layout.addWidget(editor)
        layout.addStretch()


class _ValueOverridesTab(QWidget):
    def __init__(self, session: Workspace, template: Template, catalog: GameDataCatalog) -> None:
        super().__init__()
        self._session = session
        self._template = template
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        if template.valueOverrides is None:
            template.valueOverrides = []

        editor = InlineSubObjectListEditor(
            template,
            "valueOverrides",
            session,
            factories=[("Value Override", lambda: ValueOverride(sid="new_sid"))],
            populate=lambda form, obj, refs: _populate_value_override_row(form, obj, refs, session, catalog),
            title_for_item=lambda obj, idx: f"[{idx}] {obj.sid}",
        )
        layout.addWidget(editor)
        layout.addStretch()


