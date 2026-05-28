"""Template-wide settings dialog — Basic, Game Rules, Win Conditions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from templategen.model.enums import GameMode
from templategen.model.game_rules import Bonus, GlobalBans, ValueOverride, WinConditions
from templategen.services.commands import EditFieldCommand
from templategen.ui.asset_icons import artifact_listables, sid_listables, spell_listables
from templategen.ui.widgets.field_binding import bind_int, bind_int_optional, bind_string
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
        form.addRow(
            "Faction laws exp modifier:",
            self._track_float(rules, "factionLawsExpModifier", 0.0, 10.0, 0.05, unset_display=1.0),
        )
        form.addRow(
            "Astrology exp modifier:",
            self._track_float(rules, "astrologyExpModifier", 0.0, 10.0, 0.05, unset_display=1.0),
        )
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
        unset_display: float = 0.0,
    ) -> QDoubleSpinBox:
        widget = QDoubleSpinBox()
        widget.setRange(minimum, maximum)
        widget.setSingleStep(step)
        widget.setDecimals(3)
        current = getattr(target, name)
        widget.setValue(float(current) if current is not None else unset_display)
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
        spell_choices = lambda: spell_listables(self._catalog)  # noqa: E731
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

    params = _BonusParametersWidget(bonus, session, catalog)
    refreshers.append(params.refresh)
    form.addRow("Parameters:", params)


def _populate_value_override_row(
    form: QFormLayout,
    override: ValueOverride,
    refreshers: list[Any],
    session: Workspace,
    catalog: GameDataCatalog,
) -> None:
    sid = SidPicker(
        override, "sid", session,
        choices=lambda: sid_listables(catalog, list(catalog.known_sids())),
    )
    refreshers.append(sid.refresh)
    form.addRow("Sid:", sid)

    variant = QSpinBox()
    variant.setRange(-2, 100_000)
    variant.setSpecialValueText("(none)")
    refreshers.append(bind_int_optional(variant, override, "variant", session, sentinel=-2))
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


_RESOURCE_NAMES: tuple[str, ...] = ("gold", "wood", "ore", "crystals", "mercury", "gemstones", "dust")


class _BonusParametersWidget(QWidget):
    """Bonus.parameters editor that swaps its inner widget based on the bonus's sid."""

    def __init__(self, bonus: Bonus, session: Workspace, catalog: GameDataCatalog) -> None:
        super().__init__()
        self._bonus = bonus
        self._session = session
        self._catalog = catalog
        self._current_sid: str | None = object()  # sentinel — force first build
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(2)
        self._inner: QWidget | None = None
        self._build()
        session.model_object_changed.connect(self._on_model_changed)

    def _on_model_changed(self, obj: object) -> None:
        # The sid of *this* bonus changed: swap to the right inner editor.
        if obj is self._bonus and self._bonus.sid != self._current_sid:
            self._build()

    def refresh(self) -> None:
        if self._bonus.sid != self._current_sid:
            self._build()

    def _build(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            w = item.widget() if item is not None else None
            if w is not None:
                w.deleteLater()
        self._current_sid = self._bonus.sid

        if self._bonus.sid == "add_bonus_res":
            self._inner = _ResBonusParametersEditor(self._bonus, self._session)
        elif self._bonus.sid == "add_bonus_hero_item":
            self._inner = _SingleSidParameterEditor(
                self._bonus, self._session,
                placeholder="(pick an artifact)",
                choices=lambda: artifact_listables(self._catalog),
            )
        elif self._bonus.sid == "add_bonus_hero_spell":
            self._inner = _SingleSidParameterEditor(
                self._bonus, self._session,
                placeholder="(pick a spell)",
                choices=lambda: spell_listables(self._catalog),
            )
        else:
            self._inner = ScalarListEditor(self._bonus, "parameters", self._session)
        self._layout.addWidget(self._inner)


class _ResBonusParametersEditor(QWidget):
    """Two-cell editor for `add_bonus_res` bonuses: resource name + integer amount.

    Stored as `parameters = [resource_name, str(amount)]`.
    """

    def __init__(self, bonus: Bonus, session: Workspace) -> None:
        super().__init__()
        self._bonus = bonus
        self._session = session

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        self._resource = QComboBox()
        self._resource.setEditable(True)
        self._resource.addItems(_RESOURCE_NAMES)
        completer = self._resource.completer()
        if completer is not None:
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            completer.setFilterMode(Qt.MatchFlag.MatchContains)
        row.addWidget(self._resource, stretch=1)

        self._amount = QSpinBox()
        self._amount.setRange(-1_000_000_000, 1_000_000_000)
        self._amount.setSingleStep(1)
        row.addWidget(self._amount)

        self._load_from_model()
        self._resource.activated.connect(lambda _idx: self._commit())
        self._resource.editTextChanged.connect(lambda _t: self._commit())
        self._amount.editingFinished.connect(self._commit)
        session.model_object_changed.connect(self._on_model_changed)

    def refresh(self) -> None:
        self._load_from_model()

    def _on_model_changed(self, obj: object) -> None:
        if obj is self._bonus:
            self._load_from_model()

    def _load_from_model(self) -> None:
        params = list(self._bonus.parameters or [])
        resource = str(params[0]) if len(params) >= 1 and isinstance(params[0], str) else ""
        amount_str = params[1] if len(params) >= 2 else "0"
        try:
            amount = int(amount_str)
        except (TypeError, ValueError):
            amount = 0
        self._resource.blockSignals(True)
        self._amount.blockSignals(True)
        try:
            self._resource.setCurrentText(resource)
            self._amount.setValue(amount)
        finally:
            self._resource.blockSignals(False)
            self._amount.blockSignals(False)

    def _commit(self) -> None:
        new = [self._resource.currentText().strip(), str(self._amount.value())]
        if list(self._bonus.parameters or []) == new:
            return
        self._session.execute(EditFieldCommand(self._session, self._bonus, "parameters", new))


class _SingleSidParameterEditor(QWidget):
    """Editable combo whose pick becomes `parameters = [value]` on the bonus."""

    def __init__(
        self,
        bonus: Bonus,
        session: Workspace,
        *,
        placeholder: str,
        choices,
    ) -> None:
        super().__init__()
        self._bonus = bonus
        self._session = session
        self._choices = choices

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._combo = QComboBox()
        self._combo.setEditable(True)
        self._combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self._combo.lineEdit().setPlaceholderText(placeholder)
        completer = self._combo.completer()
        if completer is not None:
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            completer.setFilterMode(Qt.MatchFlag.MatchContains)
        layout.addWidget(self._combo)

        self._populate_choices()
        self._sync_from_model()

        self._combo.activated.connect(lambda _idx: self._commit())
        line = self._combo.lineEdit()
        if line is not None:
            line.editingFinished.connect(self._commit)
        session.model_object_changed.connect(self._on_model_changed)

    def refresh(self) -> None:
        self._populate_choices()
        self._sync_from_model()

    def _on_model_changed(self, obj: object) -> None:
        if obj is self._bonus:
            self._sync_from_model()

    def _populate_choices(self) -> None:
        items = self._choices()
        from templategen.ui.widgets.listable import to_listable

        items = to_listable(items)
        if any(i.icon is not None for i in items):
            self._combo.setIconSize(QSize(24, 24))
        self._combo.blockSignals(True)
        self._combo.clear()
        for item in items:
            if item.icon is not None:
                self._combo.addItem(item.icon, item.display, item.value)
            else:
                self._combo.addItem(item.display, item.value)
        self._combo.blockSignals(False)

    def _sync_from_model(self) -> None:
        params = list(self._bonus.parameters or [])
        target = params[0] if params and isinstance(params[0], str) else ""
        self._combo.blockSignals(True)
        try:
            matched = -1
            for i in range(self._combo.count()):
                if self._combo.itemData(i) == target:
                    matched = i
                    break
            if matched >= 0:
                self._combo.setCurrentIndex(matched)
            else:
                self._combo.setEditText(target)
        finally:
            self._combo.blockSignals(False)

    def _resolve_value(self) -> str:
        text = self._combo.currentText()
        idx = self._combo.currentIndex()
        if idx >= 0 and self._combo.itemText(idx) == text:
            data = self._combo.itemData(idx)
            if isinstance(data, str):
                return data
        return text

    def _commit(self) -> None:
        value = self._resolve_value().strip()
        current = list(self._bonus.parameters or [])
        new = [value] if value else []
        if current == new:
            return
        self._session.execute(EditFieldCommand(self._session, self._bonus, "parameters", new))


class _ValueOverridesTab(QWidget):
    def __init__(self, session: Workspace, template: Template, catalog: GameDataCatalog) -> None:
        super().__init__()
        self._session = session
        self._template = template

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(8, 8, 8, 8)

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
        body_layout.addWidget(editor)
        body_layout.addStretch()

        scroll.setWidget(body)


