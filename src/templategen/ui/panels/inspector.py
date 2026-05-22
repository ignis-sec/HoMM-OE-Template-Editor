"""Inspector — contextual editor for the current selection, with drill-in navigation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from templategen.model.connection import (
    DefaultConnection,
    DirectConnection,
    GladiatorArenaConnection,
    PortalConnection,
    ProximityConnection,
    _ConnectionBase,
)
from templategen.model.content import (
    Anchor,
    ContentCountLimit,
    ContentItem,
    LimitItem,
    MandatoryContentBundle,
    PlacementRule,
)
from templategen.model.enums import ConnectionType, MainObjectType, Placement, PlayerId, RoadType
from templategen.model.game_rules import Bonus, ValueOverride
from templategen.model.layouts import (
    AmbientPickupDistribution,
    GuardedEncounterResourceFractions,
    ZoneLayout,
)
from templategen.model.main_objects import (
    AbandonedOutpostObject,
    CityObject,
    EmptyMainObject,
    GladiatorArenaObject,
    SpawnObject,
    _MainObjectBase,
)
from templategen.model.selectors import BiomeSelector, FactionSelector
from templategen.model.zone import EncounterHolesSettings, Road, Zone
from templategen.services.commands import ChangeConnectionTypeCommand
from templategen.ui.widgets.field_binding import (
    bind_bool,
    bind_choice,
    bind_float,
    bind_int,
    bind_string,
)
from templategen.ui.widgets.list_editors import (
    ReferenceListEditor,
    ScalarListEditor,
    SubObjectListEditor,
)
from templategen.ui.widgets.sid_picker import SidPicker
from templategen.ui.widgets.sub_object_form import LazySubObjectGroup

if TYPE_CHECKING:
    from collections.abc import Callable

    from templategen.catalog.game_data import GameDataCatalog
    from templategen.services.workspace import Workspace
    from templategen.ui.widgets.field_binding import Refresh


_PLAYER_VALUES = [p.value for p in PlayerId]
_PLACEMENT_VALUES = [p.value for p in Placement]
_BIOME_TYPES = ["FromList", "Match", "MatchMainObject", "MatchZone"]
_FACTION_TYPES = ["FromList", "Match"]
_ANCHOR_TYPES = ["MainObject", "Connection", "Crossroads", "Road", "Sid", "MandatoryContent"]

_CONNECTION_CLASS_BY_TYPE: dict[ConnectionType, type[_ConnectionBase]] = {
    ConnectionType.DIRECT: DirectConnection,
    ConnectionType.DEFAULT: DefaultConnection,
    ConnectionType.PORTAL: PortalConnection,
    ConnectionType.PROXIMITY: ProximityConnection,
    ConnectionType.GLADIATOR_ARENA: GladiatorArenaConnection,
}


def _readonly(text: str) -> QLabel:
    label = QLabel(text)
    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    label.setWordWrap(True)
    return label


def _describe(target: object) -> str:
    name = getattr(target, "name", None)
    type_name = type(target).__name__
    return f"{type_name} '{name}'" if name else type_name


class Inspector(QWidget):
    def __init__(self, workspace: Workspace, catalog: GameDataCatalog) -> None:
        super().__init__()
        self._session = workspace
        self._catalog = catalog
        self._view_stack: list[object] = []
        self._refreshers: list[Refresh] = []

        self.setMinimumWidth(360)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(self._scroll)

        self._inner: QWidget | None = None
        self._main: QVBoxLayout | None = None

        workspace.selection_changed.connect(self._on_selection_changed)
        workspace.template_changed.connect(lambda: self._on_selection_changed(None))
        workspace.model_object_changed.connect(self._on_model_changed)
        catalog.changed.connect(self._render_current)

        self._render_current()

    def _on_selection_changed(self, target: object | None) -> None:
        self._view_stack = [target] if target is not None else []
        self._render_current()

    def _on_model_changed(self, obj: object) -> None:
        if self._view_stack and obj is self._view_stack[-1]:
            for refresh in self._refreshers:
                refresh()

    def drill_in(self, sub_obj: object) -> None:
        self._view_stack.append(sub_obj)
        self._render_current()

    def go_back(self) -> None:
        if len(self._view_stack) > 1:
            self._view_stack.pop()
            self._render_current()

    def _render_current(self) -> None:
        self._refreshers.clear()
        self._reset_inner()

        if not self._view_stack:
            self._show_empty()
            return

        if len(self._view_stack) > 1:
            self._build_breadcrumb()

        target = self._view_stack[-1]
        self._dispatch(target)

        assert self._main is not None
        self._main.addStretch()

    def _dispatch(self, target: object) -> None:
        if isinstance(target, Zone):
            self._populate_zone(target)
        elif isinstance(target, _ConnectionBase):
            self._populate_connection(target)
        elif isinstance(target, ZoneLayout):
            self._populate_zone_layout(target)
        elif isinstance(target, MandatoryContentBundle):
            self._populate_mandatory_content(target)
        elif isinstance(target, ContentCountLimit):
            self._populate_content_count_limit(target)
        elif isinstance(target, _MainObjectBase):
            self._populate_main_object(target)
        elif isinstance(target, ContentItem):
            self._populate_content_item(target)
        elif isinstance(target, LimitItem):
            self._populate_limit_item(target)
        elif isinstance(target, PlacementRule):
            self._populate_placement_rule(target)
        elif isinstance(target, Road):
            self._populate_road(target)
        elif isinstance(target, Bonus):
            self._populate_bonus(target)
        elif isinstance(target, ValueOverride):
            self._populate_value_override(target)
        else:
            form = self._section()
            form.addRow("Type:", _readonly(type(target).__name__))

    def _reset_inner(self) -> None:
        new_inner = QWidget()
        new_main = QVBoxLayout(new_inner)
        new_main.setContentsMargins(0, 0, 0, 0)
        new_main.setSpacing(8)
        self._scroll.setWidget(new_inner)
        self._inner = new_inner
        self._main = new_main

    def _show_empty(self) -> None:
        assert self._main is not None
        hint = QLabel("Select a zone or connection on the canvas.")
        hint.setStyleSheet("color: #888;")
        hint.setWordWrap(True)
        self._main.addWidget(hint)
        self._main.addStretch()

    def _build_breadcrumb(self) -> None:
        assert self._main is not None
        bar = QWidget()
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 4)

        back = QPushButton("← Back")
        back.clicked.connect(self.go_back)
        layout.addWidget(back)

        path = " / ".join(_describe(t) for t in self._view_stack)
        label = QLabel(path)
        label.setStyleSheet("color: #888;")
        label.setWordWrap(True)
        layout.addWidget(label, stretch=1)

        self._main.addWidget(bar)

    def _section(self, title: str | None = None) -> QFormLayout:
        assert self._main is not None
        if title is None:
            container = QWidget()
            form = QFormLayout(container)
            form.setContentsMargins(0, 0, 0, 0)
            form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
            self._main.addWidget(container)
            return form
        group = QGroupBox(title)
        form = QFormLayout(group)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self._main.addWidget(group)
        return form

    # ─── Populate methods ────────────────────────────────────────────────

    def _populate_zone(self, zone: Zone) -> None:
        form = self._section()
        form.addRow("Kind:", _readonly("Zone"))
        form.addRow("Name:", self._line(zone, "name"))
        form.addRow("Size:", self._double(zone, "size", 0.01, 10.0, 0.05, decimals=2))
        form.addRow("Layout:", self._combo(zone, "layout", self._available_layouts()))

        guard = self._section("Guard tuning")
        guard.addRow("Cutoff value:", self._int(zone, "guardCutoffValue", 0, 100_000_000, 100))
        guard.addRow("Randomization:", self._double(zone, "guardRandomization", 0.0, 1.0, 0.01))
        guard.addRow("Multiplier:", self._double(zone, "guardMultiplier", 0.0, 100.0, 0.05))
        guard.addRow("Weekly increment:", self._double(zone, "guardWeeklyIncrement", 0.0, 10.0, 0.01))
        guard.addRow("Reaction distribution:", self._scalar_list(zone, "guardReactionDistribution", item_type=int))

        content = self._section("Content values")
        content.addRow("Guarded:", self._int(zone, "guardedContentValue", 0, 1_000_000_000, 1000))
        content.addRow("Guarded / area:", self._int(zone, "guardedContentValuePerArea", 0, 1_000_000, 100))
        content.addRow("Unguarded:", self._int(zone, "unguardedContentValue", 0, 1_000_000_000, 1000))
        content.addRow("Unguarded / area:", self._int(zone, "unguardedContentValuePerArea", 0, 1_000_000, 100))
        content.addRow("Resources:", self._int(zone, "resourcesValue", 0, 1_000_000_000, 1000))
        content.addRow("Resources / area:", self._int(zone, "resourcesValuePerArea", 0, 1_000_000, 100))

        refs = self._section("Content references")
        refs.addRow("Mandatory:", self._reference_list(zone, "mandatoryContent", choices=self._available_bundles))
        refs.addRow(
            "Count limits:",
            self._reference_list(zone, "contentCountLimits", choices=self._available_limits, accept_single_string=True),
        )

        pools = self._section("Content pools (external)")
        for label, field in (
            ("Guarded:", "guardedContentPool"),
            ("Unguarded:", "unguardedContentPool"),
            ("Resources:", "resourcesContentPool"),
        ):
            pools.addRow(label, self._reference_list(zone, field, choices=self._catalog.known_content_pools))

        other = self._section("Other")
        other.addRow("Diplomacy modifier:", self._double(zone, "diplomacyModifier", -10.0, 10.0, 0.05))
        other.addRow("Crossroads position:", self._int(zone, "crossroadsPosition", 0, 100, 1))

        main_objects = self._section("Main objects")
        main_objects.addRow(self._main_object_list(zone))

        roads = self._section("Roads")
        roads.addRow(self._road_list(zone))

        self._add_sub_group(
            "Zone biome",
            zone,
            "zoneBiome",
            lambda: BiomeSelector(type="FromList"),
            self._populate_biome_selector,
        )
        self._add_sub_group(
            "Content biome",
            zone,
            "contentBiome",
            lambda: BiomeSelector(type="FromList"),
            self._populate_biome_selector,
        )
        self._add_sub_group(
            "Meta-objects biome",
            zone,
            "metaObjectsBiome",
            lambda: BiomeSelector(type="FromList"),
            self._populate_biome_selector,
        )
        self._add_sub_group(
            "Encounter holes",
            zone,
            "encounterHolesSettings",
            EncounterHolesSettings,
            self._populate_encounter_holes,
        )

    def _populate_connection(self, conn: _ConnectionBase) -> None:
        form = self._section()
        form.addRow("Kind:", _readonly("Connection"))
        form.addRow("Type:", self._connection_type_picker(conn))
        form.addRow("Name:", self._line(conn, "name", optional=True))
        form.addRow("From:", _readonly(conn.from_))
        form.addRow("To:", _readonly(conn.to))

        road = self._section("Road")
        road.addRow("Has road:", self._check(conn, "road"))
        road.addRow("Gate placement:", self._line(conn, "gatePlacement", optional=True))

        guard = self._section("Guard")
        guard.addRow("Value:", self._int(conn, "guardValue", 0, 1_000_000_000, 1000))
        guard.addRow("Weekly increment:", self._double(conn, "guardWeeklyIncrement", 0.0, 10.0, 0.01))
        guard.addRow("Randomization:", self._double(conn, "guardRandomization", 0.0, 1.0, 0.01))
        guard.addRow("Allow escape:", self._check(conn, "guardEscape"))
        guard.addRow("Guard zone:", self._line(conn, "guardZone", optional=True))
        guard.addRow("Match group:", self._line(conn, "guardMatchGroup", optional=True))
        guard.addRow("Sim turn squad:", self._check(conn, "simTurnSquad"))

        if isinstance(conn, ProximityConnection):
            prox = self._section("Proximity")
            prox.addRow("Length:", self._double(conn, "length", 0.0, 100.0, 0.05))

    def _populate_zone_layout(self, layout: ZoneLayout) -> None:
        form = self._section()
        form.addRow("Kind:", _readonly("Zone Layout"))
        form.addRow("Name:", self._line(layout, "name"))

        terrain = self._section("Terrain")
        terrain.addRow("Obstacles fill:", self._double(layout, "obstaclesFill", 0.0, 1.0, 0.01))
        terrain.addRow("Obstacles fill (void):", self._double(layout, "obstaclesFillVoid", 0.0, 1.0, 0.01))
        terrain.addRow("Lakes fill:", self._double(layout, "lakesFill", 0.0, 1.0, 0.01))
        terrain.addRow("Min lake area:", self._int(layout, "minLakeArea", 0, 10_000, 1))

        elevation = self._section("Elevation")
        elevation.addRow("Cluster scale:", self._double(layout, "elevationClusterScale", 0.0, 10.0, 0.01))
        modes = layout.elevationModes or []
        elevation.addRow("Modes:", _readonly(f"{len(modes)} mode(s)"))

        roads = self._section("Roads")
        roads.addRow("Road cluster area:", self._int(layout, "roadClusterArea", 0, 100_000, 1))

        self._add_sub_group(
            "Guarded encounter resource fractions",
            layout,
            "guardedEncounterResourceFractions",
            GuardedEncounterResourceFractions,
            self._populate_encounter_resource_fractions,
        )
        self._add_sub_group(
            "Ambient pickup distribution",
            layout,
            "ambientPickupDistribution",
            AmbientPickupDistribution,
            self._populate_ambient_pickup,
        )

    def _populate_mandatory_content(self, bundle: MandatoryContentBundle) -> None:
        form = self._section()
        form.addRow("Kind:", _readonly("Mandatory Content Bundle"))
        form.addRow("Name:", self._line(bundle, "name"))

        content = self._section("Content items")
        content.addRow(self._content_item_list(bundle, "content"))

    def _populate_content_count_limit(self, limit: ContentCountLimit) -> None:
        form = self._section()
        form.addRow("Kind:", _readonly("Content Count Limit"))
        form.addRow("Name:", self._line(limit, "name"))

        entries = self._section("Limit entries")
        entries.addRow(self._limit_item_list(limit, "limits"))

    def _populate_main_object(self, mo: _MainObjectBase) -> None:
        form = self._section()
        form.addRow("Kind:", _readonly(f"Main Object ({mo.type.value})"))
        form.addRow("Placement:", self._combo(mo, "placement", _PLACEMENT_VALUES))
        form.addRow("Placement args:", self._scalar_list(mo, "placementArgs"))

        if isinstance(mo, SpawnObject):
            form.addRow("Spawn (player):", self._combo(mo, "spawn", _PLAYER_VALUES))

        guard = self._section("Guard")
        guard.addRow("Chance:", self._double(mo, "guardChance", 0.0, 1.0, 0.05))
        guard.addRow("Value:", self._int(mo, "guardValue", 0, 1_000_000_000, 1000))
        guard.addRow("Weekly increment:", self._double(mo, "guardWeeklyIncrement", 0.0, 10.0, 0.01))
        guard.addRow("Randomization:", self._double(mo, "guardRandomization", 0.0, 1.0, 0.01))
        guard.addRow("Remove if has owner:", self._check(mo, "removeGuardIfHasOwner"))

        misc = self._section("Misc")
        misc.addRow(
            "Buildings construction sid:",
            self._editable_combo(
                mo,
                "buildingsConstructionSid",
                choices=self._catalog.known_building_constructions,
            ),
        )
        misc.addRow("Owner:", self._combo(mo, "owner", _PLAYER_VALUES))
        misc.addRow("Factions:", self._scalar_list(mo, "factions"))
        misc.addRow("Is key object:", self._check(mo, "isKeyObject"))
        misc.addRow("Hold city win con:", self._check(mo, "holdCityWinCon"))
        misc.addRow("Enable weekly unit inc:", self._check(mo, "enableWeeklyUnitIncrement"))
        misc.addRow("Initial unit increment:", self._double(mo, "initialUnitIncrement", 0.0, 100.0, 0.05))

        self._add_sub_group(
            "Faction selector",
            mo,
            "faction",
            lambda: FactionSelector(type="FromList"),
            self._populate_faction_selector,
        )

    def _populate_content_item(self, item: ContentItem) -> None:
        form = self._section()
        form.addRow("Kind:", _readonly("Content Item"))
        form.addRow("Sid:", self._sid_picker(item, "sid"))
        form.addRow("Variant:", self._int(item, "variant", -1, 100_000, 1))
        form.addRow("Name:", self._line(item, "name", optional=True))

        flags = self._section("Flags")
        flags.addRow("Is mine:", self._check(item, "isMine"))
        flags.addRow("Is guarded:", self._check(item, "isGuarded"))
        flags.addRow("Solo encounter:", self._check(item, "soloEncounter"))
        flags.addRow("Designated encounter:", self._check(item, "designatedEncounter"))
        flags.addRow("Road:", self._check(item, "road"))

        owner_section = self._section("Owner / Guard")
        owner_section.addRow("Owner:", self._combo(item, "owner", _PLAYER_VALUES))
        owner_section.addRow("Guard value:", self._int(item, "guardValue", 0, 1_000_000_000, 1000))

        lists = self._section("Reference lists")
        lists.addRow(
            "Include lists:",
            self._reference_list(item, "includeLists", choices=self._catalog.known_content_lists),
        )

        rules = self._section("Placement rules")
        rules.addRow(self._placement_rule_list(item, "rules"))

    def _populate_limit_item(self, item: LimitItem) -> None:
        form = self._section()
        form.addRow("Kind:", _readonly("Limit Item"))
        form.addRow("Sid:", self._sid_picker(item, "sid"))
        form.addRow("Variant:", self._int(item, "variant", -1, 100_000, 1))
        form.addRow("Max count:", self._int(item, "maxCount", 0, 1_000_000, 1))

        lists = self._section("Reference lists")
        lists.addRow(
            "Include lists:",
            self._reference_list(item, "includeLists", choices=self._catalog.known_content_lists),
        )

        content = self._section("Content items")
        content.addRow(self._content_item_list(item, "content"))

    def _populate_placement_rule(self, rule: PlacementRule) -> None:
        form = self._section()
        form.addRow("Kind:", _readonly("Placement Rule"))
        form.addRow("Type:", self._combo(rule, "type", _ANCHOR_TYPES))
        form.addRow("Args:", self._scalar_list(rule, "args"))
        form.addRow("Target min:", self._double(rule, "targetMin", 0.0, 1.0, 0.01))
        form.addRow("Target max:", self._double(rule, "targetMax", 0.0, 1.0, 0.01))
        form.addRow("Target (alt):", self._double(rule, "target", 0.0, 1.0, 0.01))
        form.addRow("Weight:", self._double(rule, "weight", 0.0, 100.0, 0.5))

    def _populate_road(self, road: Road) -> None:
        form = self._section()
        form.addRow("Kind:", _readonly("Road"))
        road_types = ["", "Stone", "Dirt"]
        form.addRow("Type:", self._combo(road, "type", road_types))

        self._add_sub_group(
            "From anchor",
            road,
            "from_",
            lambda: Anchor(type="MainObject"),
            self._populate_anchor,
        )
        self._add_sub_group(
            "To anchor",
            road,
            "to",
            lambda: Anchor(type="MainObject"),
            self._populate_anchor,
        )

    def _populate_bonus(self, bonus: Bonus) -> None:
        form = self._section()
        form.addRow("Kind:", _readonly("Bonus"))
        form.addRow("Sid:", self._line(bonus, "sid"))
        form.addRow("Receiver side:", self._int(bonus, "receiverSide", -1, 32, 1))
        form.addRow("Receiver filter:", self._line(bonus, "receiverFilter", optional=True))
        form.addRow("Parameters:", self._scalar_list(bonus, "parameters"))

    def _populate_value_override(self, override: ValueOverride) -> None:
        form = self._section()
        form.addRow("Kind:", _readonly("Value Override"))
        form.addRow("Sid:", self._line(override, "sid"))
        form.addRow("Variant:", self._int(override, "variant", -1, 100_000, 1))
        form.addRow("Guard value:", self._int(override, "guardValue", 0, 1_000_000_000, 1000))

    # ─── Sub-group populates (inline forms) ───────────────────────────────

    def _populate_biome_selector(
        self,
        form: QFormLayout,
        selector: BiomeSelector,
        refreshers: list[Refresh],
    ) -> None:
        combo = QComboBox()
        refreshers.append(bind_choice(combo, selector, "type", self._session, _BIOME_TYPES))
        form.addRow("Type:", combo)

        biomes = list(self._catalog.known_biomes())
        if biomes:
            args = ReferenceListEditor(selector, "args", self._session, choices=self._catalog.known_biomes)
        else:
            args = ScalarListEditor(selector, "args", self._session)
        refreshers.append(args.refresh)
        form.addRow("Args:", args)

    def _populate_faction_selector(
        self,
        form: QFormLayout,
        selector: FactionSelector,
        refreshers: list[Refresh],
    ) -> None:
        combo = QComboBox()
        refreshers.append(bind_choice(combo, selector, "type", self._session, _FACTION_TYPES))
        form.addRow("Type:", combo)

        args = ScalarListEditor(selector, "args", self._session)
        refreshers.append(args.refresh)
        form.addRow("Args:", args)

    def _populate_anchor(
        self,
        form: QFormLayout,
        anchor: Anchor,
        refreshers: list[Refresh],
    ) -> None:
        combo = QComboBox()
        refreshers.append(bind_choice(combo, anchor, "type", self._session, _ANCHOR_TYPES))
        # Switching the anchor's type changes which kind of args editor is appropriate,
        # so trigger a full re-render of the current view when the user picks a new type.
        # Defer via QTimer so we don't delete the combo from inside its own signal handler
        # (which would segfault when Qt unwinds back through the destroyed widget).
        combo.activated.connect(lambda _idx: QTimer.singleShot(0, self._render_current))
        form.addRow("Type:", combo)

        if anchor.type == "Connection":
            zone, variant = self._zone_for_anchor(anchor)
            if zone is not None and variant is not None:
                conn_names = [
                    c.name for c in variant.connections
                    if c.name and (c.from_ == zone.name or c.to == zone.name)
                ]
                args: QWidget = ReferenceListEditor(
                    anchor, "args", self._session, choices=lambda names=conn_names: names
                )
            else:
                args = ScalarListEditor(anchor, "args", self._session)
        else:
            args = ScalarListEditor(anchor, "args", self._session)
        refreshers.append(args.refresh)
        form.addRow("Args:", args)

    def _zone_for_anchor(self, anchor: Anchor) -> tuple[Zone | None, object | None]:
        template = self._session.template
        if template is None:
            return None, None
        for variant in template.variants:
            for zone in variant.zones:
                for road in zone.roads or []:
                    if road.from_ is anchor or road.to is anchor:
                        return zone, variant
        return None, None

    def _populate_encounter_holes(
        self,
        form: QFormLayout,
        settings: EncounterHolesSettings,
        refreshers: list[Refresh],
    ) -> None:
        affected = QDoubleSpinBox()
        affected.setRange(0.0, 1.0)
        affected.setSingleStep(0.01)
        affected.setDecimals(3)
        refreshers.append(bind_float(affected, settings, "affectedEncounters", self._session))
        form.addRow("Affected encounters:", affected)

        two = QDoubleSpinBox()
        two.setRange(0.0, 1.0)
        two.setSingleStep(0.01)
        two.setDecimals(3)
        refreshers.append(bind_float(two, settings, "twoHoleEncounters", self._session))
        form.addRow("Two-hole encounters:", two)

    def _populate_encounter_resource_fractions(
        self,
        form: QFormLayout,
        fractions: GuardedEncounterResourceFractions,
        refreshers: list[Refresh],
    ) -> None:
        bounds = ScalarListEditor(fractions, "countBounds", self._session, item_type=int)
        refreshers.append(bounds.refresh)
        form.addRow("Count bounds:", bounds)

        fracs = ScalarListEditor(fractions, "fractions", self._session)
        refreshers.append(fracs.refresh)
        form.addRow("Fractions:", fracs)

    def _populate_ambient_pickup(
        self,
        form: QFormLayout,
        dist: AmbientPickupDistribution,
        refreshers: list[Refresh],
    ) -> None:
        for label, field in (
            ("Repulsion:", "repulsion"),
            ("Noise:", "noise"),
            ("Road attraction:", "roadAttraction"),
            ("Obstacle attraction:", "obstacleAttraction"),
        ):
            widget = QDoubleSpinBox()
            widget.setRange(-10.0, 10.0)
            widget.setSingleStep(0.05)
            widget.setDecimals(3)
            refreshers.append(bind_float(widget, dist, field, self._session))
            form.addRow(label, widget)

        weights = ScalarListEditor(dist, "groupSizeWeights", self._session, item_type=int)
        refreshers.append(weights.refresh)
        form.addRow("Group size weights:", weights)

    # ─── List editor factories with drill-in ──────────────────────────────

    def _main_object_list(self, zone: Zone) -> SubObjectListEditor:
        factories: list[tuple[str, Callable[[], object]]] = [
            ("Spawn", lambda: SpawnObject()),
            ("City", lambda: CityObject()),
            ("Abandoned Outpost", lambda: AbandonedOutpostObject()),
            ("Gladiator Arena", lambda: GladiatorArenaObject()),
            ("Empty placeholder", lambda: EmptyMainObject()),
        ]

        def summary(mo: object) -> str:
            type_label = getattr(mo, "type", None)
            if isinstance(type_label, MainObjectType):
                base = type_label.value
            elif isinstance(mo, EmptyMainObject):
                base = "Empty"
            else:
                base = type(mo).__name__
            extra = ""
            if isinstance(mo, SpawnObject) and mo.spawn is not None:
                extra = f" ({mo.spawn.value})"
            return f"{base}{extra}"

        return SubObjectListEditor(
            zone,
            "mainObjects",
            self._session,
            factories=factories,
            summary=summary,
            on_drill_in=self.drill_in,
        )

    def _road_list(self, zone: Zone) -> SubObjectListEditor:
        factories: list[tuple[str, Callable[[], object]]] = [
            (
                "Road",
                lambda: Road(
                    type=RoadType.STONE,
                    **{
                        "from": Anchor(type="MainObject", args=["0"]),
                        "to": Anchor(type="MainObject", args=["0"]),
                    },
                ),
            ),
        ]

        def anchor_str(anchor: Anchor) -> str:
            args = list(anchor.args) if anchor.args else []
            return f"{anchor.type}[{', '.join(str(a) for a in args)}]" if args else anchor.type

        def summary(road: object) -> str:
            assert isinstance(road, Road)
            type_text = road.type.value if road.type else "no road"
            return f"{type_text}: {anchor_str(road.from_)} → {anchor_str(road.to)}"

        return SubObjectListEditor(
            zone,
            "roads",
            self._session,
            factories=factories,
            summary=summary,
            on_drill_in=self.drill_in,
        )

    def _content_item_list(self, target: object, field: str) -> SubObjectListEditor:
        factories: list[tuple[str, Callable[[], object]]] = [
            ("Content Item", lambda: ContentItem()),
        ]

        def summary(item: object) -> str:
            assert isinstance(item, ContentItem)
            if item.sid:
                tail = f" (sid={item.sid})"
            elif item.includeLists:
                tail = f" (lists={','.join(item.includeLists)})"
            else:
                tail = ""
            return f"ContentItem{tail}"

        return SubObjectListEditor(
            target,
            field,
            self._session,
            factories=factories,
            summary=summary,
            on_drill_in=self.drill_in,
        )

    def _limit_item_list(self, target: object, field: str) -> SubObjectListEditor:
        factories: list[tuple[str, Callable[[], object]]] = [
            ("Limit Item", lambda: LimitItem(maxCount=1)),
        ]

        def summary(item: object) -> str:
            assert isinstance(item, LimitItem)
            head = item.sid or ("via includeLists" if item.includeLists else "(no sid)")
            return f"{head} (max={item.maxCount})"

        return SubObjectListEditor(
            target,
            field,
            self._session,
            factories=factories,
            summary=summary,
            on_drill_in=self.drill_in,
        )

    def _placement_rule_list(self, target: object, field: str) -> SubObjectListEditor:
        factories: list[tuple[str, Callable[[], object]]] = [
            ("Placement Rule", lambda: PlacementRule(type="MainObject")),
        ]

        def summary(rule: object) -> str:
            assert isinstance(rule, PlacementRule)
            return f"{rule.type} args={rule.args}"

        return SubObjectListEditor(
            target,
            field,
            self._session,
            factories=factories,
            summary=summary,
            on_drill_in=self.drill_in,
        )

    # ─── Reusable widget factories ────────────────────────────────────────

    def _available_layouts(self) -> list[str]:
        template = self._session.template
        if template is None:
            return []
        return [zl.name for zl in template.zoneLayouts]

    def _available_bundles(self) -> list[str]:
        template = self._session.template
        if template is None:
            return []
        return [b.name for b in template.mandatoryContent]

    def _available_limits(self) -> list[str]:
        template = self._session.template
        if template is None:
            return []
        return [c.name for c in template.contentCountLimits]

    def _line(self, target: object, field: str, *, optional: bool = False) -> QLineEdit:
        widget = QLineEdit()
        self._refreshers.append(bind_string(widget, target, field, self._session, optional=optional))
        return widget

    def _int(self, target: object, field: str, minimum: int, maximum: int, step: int) -> QSpinBox:
        widget = QSpinBox()
        widget.setRange(minimum, maximum)
        widget.setSingleStep(step)
        self._refreshers.append(bind_int(widget, target, field, self._session))
        return widget

    def _double(
        self,
        target: object,
        field: str,
        minimum: float,
        maximum: float,
        step: float,
        *,
        decimals: int = 3,
    ) -> QDoubleSpinBox:
        widget = QDoubleSpinBox()
        widget.setRange(minimum, maximum)
        widget.setSingleStep(step)
        widget.setDecimals(decimals)
        self._refreshers.append(bind_float(widget, target, field, self._session))
        return widget

    def _check(self, target: object, field: str) -> QCheckBox:
        widget = QCheckBox()
        self._refreshers.append(bind_bool(widget, target, field, self._session))
        return widget

    def _combo(self, target: object, field: str, choices: list[str]) -> QComboBox:
        widget = QComboBox()
        self._refreshers.append(bind_choice(widget, target, field, self._session, choices))
        return widget

    def _sid_picker(self, target: object, field: str) -> SidPicker:
        widget = SidPicker(target, field, self._session, choices=self._catalog.known_sids)
        self._refreshers.append(widget.refresh)
        return widget

    def _connection_type_picker(self, conn: _ConnectionBase) -> QComboBox:
        widget = QComboBox()
        values = list(_CONNECTION_CLASS_BY_TYPE)
        widget.addItems([t.value for t in values])
        widget.setCurrentIndex(values.index(conn.connectionType))

        def on_changed(_index: int) -> None:
            picked = values[widget.currentIndex()]
            if picked == conn.connectionType:
                return
            variant = self._find_variant_containing(conn)
            if variant is None:
                return
            new_class = _CONNECTION_CLASS_BY_TYPE[picked]
            self._session.execute(ChangeConnectionTypeCommand(self._session, variant, conn, new_class))

        widget.activated.connect(on_changed)
        return widget

    def _find_variant_containing(self, conn: _ConnectionBase) -> object | None:
        template = self._session.template
        if template is None:
            return None
        for variant in template.variants:
            if any(c is conn for c in variant.connections):
                return variant
        return None

    def _editable_combo(
        self,
        target: object,
        field: str,
        *,
        choices: Callable[[], list[str]],
    ) -> SidPicker:
        widget = SidPicker(target, field, self._session, choices=choices)
        self._refreshers.append(widget.refresh)
        return widget

    def _scalar_list(
        self,
        target: object,
        field: str,
        *,
        item_type: type = str,
    ) -> ScalarListEditor:
        widget = ScalarListEditor(target, field, self._session, item_type=item_type)
        self._refreshers.append(widget.refresh)
        return widget

    def _reference_list(
        self,
        target: object,
        field: str,
        *,
        choices: Callable[[], list[str]],
        accept_single_string: bool = False,
    ) -> ReferenceListEditor:
        widget = ReferenceListEditor(
            target,
            field,
            self._session,
            choices=choices,
            accept_single_string=accept_single_string,
        )
        self._refreshers.append(widget.refresh)
        return widget

    def _add_sub_group(
        self,
        title: str,
        parent_target: object,
        field: str,
        factory: Callable[[], object],
        populate: Callable[[QFormLayout, object, list[Refresh]], None],
    ) -> None:
        assert self._main is not None
        group = LazySubObjectGroup(title, parent_target, field, factory, populate, self._session)
        self._main.addWidget(group)
