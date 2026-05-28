"""GraphScene — renders the current Variant either as a zone graph (zones + connections,
the default editing view) or as a road graph (one node per MainObject + one node per
referenced bundle ContentItem + one node per connection, with roads drawn between them).
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Final

from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QGraphicsScene

from templategen.model.connection import (
    DefaultConnection,
    DirectConnection,
    GladiatorArenaConnection,
    PortalConnection,
    ProximityConnection,
)
from templategen.model.content import Anchor as AnchorRuntime
from templategen.model.content import ContentItem as ContentItemRuntime
from templategen.model.enums import ConnectionType, MainObjectType, RoadType
from templategen.model.main_objects import (
    AbandonedOutpostObject,
    CityObject,
    EmptyMainObject,
    GladiatorArenaObject,
    SpawnObject,
)
from templategen.model.variant import Variant
from templategen.model.zone import Road, Zone
from templategen.ui.canvas.connection_item import EdgeItem
from templategen.ui.canvas.layout import compute_layout
from templategen.ui.canvas.object_node import ConnectionNode, ObjectNode, RoadEdgeItem
from templategen.ui.canvas.zone_item import ZoneItem
from templategen.ui.canvas.zone_style import _PLAYER_COLOR, compute_zone_styles

if TYPE_CHECKING:
    from PySide6.QtGui import QIcon

    from templategen.catalog.game_data import GameDataCatalog
    from templategen.model.content import Anchor, ContentItem
    from templategen.services.session import EditorSession

_SCENE_SIZE: Final[float] = 1200.0
_LAYOUT_SCALE: Final[float] = 500.0
_PARALLEL_SPACING: Final[float] = 12.0
_OBJECT_FAN_RADIUS: Final[float] = 38.0


class GraphScene(QGraphicsScene):
    def __init__(self, session: EditorSession, catalog: GameDataCatalog | None = None) -> None:
        super().__init__()
        self._session = session
        self._catalog = catalog
        self._zone_items: dict[str, ZoneItem] = {}
        self._road_object_items: dict[str, ObjectNode] = {}
        self._road_connection_items: dict[str, ConnectionNode] = {}
        # Cached positions persist across rebuilds AND across mode switches, so
        # user drags survive things like add/remove road, toggling show-all, and
        # flipping back and forth between zone and road views.
        self._cached_zone_positions: dict[str, QPointF] = {}
        self._cached_road_positions: dict[str, QPointF] = {}
        self._pending_positions: dict[str, QPointF] = {}
        self._show_roads: bool = False
        self._show_all_objects: bool = False

        self.setSceneRect(-_SCENE_SIZE / 2, -_SCENE_SIZE / 2, _SCENE_SIZE, _SCENE_SIZE)

        session.template_changed.connect(self.rebuild)
        session.current_variant_changed.connect(self.rebuild)
        session.model_object_changed.connect(self._refresh_for)
        self.selectionChanged.connect(self._forward_selection)

        self.rebuild()

    @property
    def session(self) -> EditorSession:
        return self._session

    @property
    def current_variant(self) -> Variant | None:
        template = self._session.template
        if not template or not template.variants:
            return None
        idx = self._session.current_variant_index
        if not 0 <= idx < len(template.variants):
            return None
        return template.variants[idx]

    @property
    def zone_items(self) -> dict[str, ZoneItem]:
        return dict(self._zone_items)

    def stage_position(self, zone_name: str, scene_pos: QPointF) -> None:
        self._pending_positions[zone_name] = QPointF(scene_pos)

    def set_show_roads(self, show: bool) -> None:
        if show == self._show_roads:
            return
        self._show_roads = show
        self.rebuild()

    @property
    def show_roads(self) -> bool:
        return self._show_roads

    def set_show_all_objects(self, show: bool) -> None:
        if show == self._show_all_objects:
            return
        self._show_all_objects = show
        if self._show_roads:
            self.rebuild()

    @property
    def show_all_objects(self) -> bool:
        return self._show_all_objects

    def current_zone_positions(self) -> dict[str, tuple[float, float]]:
        """Latest known zone positions, regardless of current mode. Pulled from
        live ZoneItems when in zone view, falls back to the persistent cache
        (which was last updated at rebuild time)."""
        if self._zone_items:
            return {n: (it.pos().x(), it.pos().y()) for n, it in self._zone_items.items()}
        return {n: (p.x(), p.y()) for n, p in self._cached_zone_positions.items()}

    def current_road_node_positions(self) -> dict[str, tuple[float, float]]:
        """Latest known road-graph node positions, keyed by stable string."""
        out: dict[str, tuple[float, float]] = {}
        for key, node in self._road_object_items.items():
            out[key] = (node.pos().x(), node.pos().y())
        for key, node in self._road_connection_items.items():
            out[key] = (node.pos().x(), node.pos().y())
        # Include positions cached from previous rebuilds for nodes that aren't
        # currently in the scene (e.g. the user is in zone mode at save time).
        for key, p in self._cached_road_positions.items():
            out.setdefault(key, (p.x(), p.y()))
        return out

    def create_road_between(
        self, source_node: ObjectNode | ConnectionNode, target_node: ObjectNode | ConnectionNode
    ) -> str | None:
        """Add the road(s) needed to link two road-graph nodes.

        Returns None on success, or a human-readable error string. Handles three
        cases:
          - both endpoints sit in the same zone → one road in that zone;
          - endpoints sit in different zones with a non-proximity connection
            linking them → two roads (one per zone) plus toggling `road = True`
            on the bridge connection;
          - otherwise refuses with an explanatory error.
        All mutations run inside a single undo macro.
        """
        variant = self.current_variant
        if variant is None:
            return "No current variant."
        template = self._session.template
        if template is None:
            return "No template loaded."

        plan = self._plan_road(source_node, target_node, variant, template)
        if isinstance(plan, str):
            return plan

        from templategen.services.commands import AddListItemCommand, EditFieldCommand

        session = self._session
        label = "Add road" if len(plan) == 1 else "Add road (multi-zone)"
        session.begin_macro(label)
        try:
            for zone, src_anchor, dst_anchor, bridge_conn in plan:
                if zone.roads is None:
                    session.execute(EditFieldCommand(session, zone, "roads", []))
                road = Road(type=RoadType.STONE, from_=src_anchor, to=dst_anchor)
                session.execute(AddListItemCommand(session, zone, "roads", road))
                if bridge_conn is not None and not bridge_conn.road:
                    session.execute(EditFieldCommand(session, bridge_conn, "road", True))
        finally:
            session.end_macro()
        return None

    def _plan_road(
        self,
        source: ObjectNode | ConnectionNode,
        target: ObjectNode | ConnectionNode,
        variant: Variant,
        template: object,
    ) -> list[tuple[Zone, AnchorRuntime, AnchorRuntime, object | None]] | str:
        if source is target:
            return "Source and target are the same node."

        src_zone_names = _zones_containing_node(source.model_target, variant, template)
        dst_zone_names = _zones_containing_node(target.model_target, variant, template)
        if not src_zone_names:
            return "Source has no zone."
        if not dst_zone_names:
            return "Target has no zone."

        # Same-zone road — pick any zone owned by both.
        for zone in variant.zones:
            if zone.name in src_zone_names and zone.name in dst_zone_names:
                sa = _anchor_for_in_zone(source.model_target, zone, template)
                da = _anchor_for_in_zone(target.model_target, zone, template)
                if sa is None or da is None:
                    continue
                return [(zone, sa, da, None)]

        # Bridge through a connection. Skip proximity — they aren't road-routable.
        for conn in variant.connections:
            if conn.connectionType == ConnectionType.PROXIMITY:
                continue
            if conn.name is None:
                continue
            a_zone = _zone_by_name(conn.from_, variant)
            b_zone = _zone_by_name(conn.to, variant)
            if a_zone is None or b_zone is None:
                continue
            if a_zone.name in src_zone_names and b_zone.name in dst_zone_names:
                zone_a, zone_b = a_zone, b_zone
            elif b_zone.name in src_zone_names and a_zone.name in dst_zone_names:
                zone_a, zone_b = b_zone, a_zone
            else:
                continue
            sa = _anchor_for_in_zone(source.model_target, zone_a, template)
            da = _anchor_for_in_zone(target.model_target, zone_b, template)
            if sa is None or da is None:
                continue
            conn_anchor = AnchorRuntime(type="Connection", args=[conn.name])
            return [
                (zone_a, sa, conn_anchor, conn),
                (zone_b, conn_anchor, da, conn),
            ]

        return "No non-proximity connection links the source and target zones."

    def rebuild(self) -> None:
        # Snapshot positions of everything currently on the scene into the long-
        # lived caches so they survive both rebuilds and zone↔road mode switches.
        for name, item in self._zone_items.items():
            self._cached_zone_positions[name] = item.pos()
        for key, node in self._road_object_items.items():
            self._cached_road_positions[key] = node.pos()
        for key, node in self._road_connection_items.items():
            self._cached_road_positions[key] = node.pos()

        loaded_zone_positions: dict[str, tuple[float, float]] = {}
        loaded_road_positions: dict[str, tuple[float, float]] = {}
        # Only consume the PNG-loaded positions once per template load: while we
        # have no cached state at all, treat this as the initial rebuild.
        if not self._cached_zone_positions and not self._cached_road_positions:
            consume_zones = getattr(self._session, "consume_loaded_positions", None)
            if callable(consume_zones):
                loaded_zone_positions = consume_zones()
            consume_roads = getattr(self._session, "consume_loaded_road_node_positions", None)
            if callable(consume_roads):
                loaded_road_positions = consume_roads()

        self.clear()
        self._zone_items.clear()
        self._road_object_items.clear()
        self._road_connection_items.clear()

        variant = self.current_variant
        if variant is None:
            return

        # Resolve a position per zone — same source whether we render zones or roads.
        layout_positions = compute_layout(variant) if variant.zones else {}
        zone_positions: dict[str, QPointF] = {}
        for zone in variant.zones:
            if zone.name in self._pending_positions:
                pos = self._pending_positions.pop(zone.name)
            elif zone.name in self._cached_zone_positions:
                pos = self._cached_zone_positions[zone.name]
            elif zone.name in loaded_zone_positions:
                lx, ly = loaded_zone_positions[zone.name]
                pos = QPointF(lx, ly)
            else:
                x, y = layout_positions[zone.name]
                pos = QPointF(x * _LAYOUT_SCALE, y * _LAYOUT_SCALE)
            zone_positions[zone.name] = pos

        # Whatever positions we just resolved for zones are also the live truth —
        # write them back so subsequent toggles see the current state even before
        # the user touches anything.
        self._cached_zone_positions = dict(zone_positions)
        # Merge any PNG-loaded road positions so first-rebuild restores them.
        for key, (x, y) in loaded_road_positions.items():
            self._cached_road_positions.setdefault(key, QPointF(x, y))

        if self._show_roads:
            self._build_road_graph(variant, zone_positions)
        else:
            self._build_zone_graph(variant, zone_positions)

        self.update()

    # ── Zone-graph mode (default) ─────────────────────────────────────────

    def _build_zone_graph(self, variant: Variant, positions: dict[str, QPointF]) -> None:
        styles = compute_zone_styles(variant)
        for zone in variant.zones:
            style = styles[zone.name]
            item = ZoneItem(zone, radius=style.radius, fill=style.fill)
            item.setPos(positions[zone.name])
            self.addItem(item)
            self._zone_items[zone.name] = item

        offsets_by_id = _parallel_offsets(variant.connections)
        for conn in variant.connections:
            source = self._zone_items.get(conn.from_)
            target = self._zone_items.get(conn.to)
            if source is None or target is None:
                continue
            edge = EdgeItem(conn, source, target, parallel_offset=offsets_by_id.get(id(conn), 0.0))
            self.addItem(edge)

    # ── Road-graph mode ───────────────────────────────────────────────────

    def _build_road_graph(self, variant: Variant, positions: dict[str, QPointF]) -> None:
        template = self._session.template
        bundle_by_name = (
            {b.name: b for b in template.mandatoryContent} if template is not None else {}
        )

        # For each zone, we render: every MainObject + (optionally) bundle ContentItems
        # reachable from `zone.mandatoryContent`. In default mode only items actually
        # referenced by one of the zone's road anchors are shown; with show_all_objects
        # every named ContentItem from the referenced bundles is drawn.
        zone_main_nodes: dict[str, list[ObjectNode]] = {}
        zone_content_nodes: dict[str, dict[str, ObjectNode]] = {}

        for zone in variant.zones:
            ref_content_names = _content_anchor_refs(zone)
            content_items = _resolvable_content_items(
                zone, bundle_by_name, ref_content_names, self._show_all_objects
            )

            # Each node gets a stable key (`mo:zone:idx`, `ci:zone:name`) so its
            # position survives rebuilds even when the underlying Python object
            # is replaced (e.g. after add/remove road).
            mo_nodes: list[ObjectNode] = []
            mo_keys: list[str] = []
            for i, mo in enumerate(zone.mainObjects):
                node = _object_node_for(mo, zone, i)
                key = _key_for_main_object(zone.name, i)
                mo_nodes.append(node)
                mo_keys.append(key)

            content_node_list: list[ObjectNode] = []
            content_node_keys: list[str | None] = []
            content_nodes: dict[str, ObjectNode] = {}
            for item in content_items:
                node = _content_node_for(item, zone, self._catalog)
                content_node_list.append(node)
                content_node_keys.append(_key_for_content_item(zone.name, item.name))
                if item.name is not None:
                    content_nodes[item.name] = node

            all_nodes: list[ObjectNode] = list(mo_nodes) + content_node_list
            all_keys: list[str | None] = list(mo_keys) + content_node_keys
            zone_pos = positions[zone.name]
            for i, (node, key) in enumerate(zip(all_nodes, all_keys, strict=True)):
                if key is not None and key in self._cached_road_positions:
                    node.setPos(self._cached_road_positions[key])
                else:
                    node.setPos(zone_pos + _fan_offset(i, len(all_nodes)))
                self.addItem(node)
                if key is not None:
                    self._road_object_items[key] = node

            zone_main_nodes[zone.name] = mo_nodes
            zone_content_nodes[zone.name] = content_nodes

        # Connection nodes — midpoint between the two zone positions. Proximity
        # connections aren't road-routable, so they're omitted from the graph
        # (and from the "Add Road" tool's pool of bridge connections).
        connection_nodes: dict[str, ConnectionNode] = {}
        for conn in variant.connections:
            if conn.name is None:
                continue
            if conn.connectionType == ConnectionType.PROXIMITY:
                continue
            src = positions.get(conn.from_)
            dst = positions.get(conn.to)
            if src is None or dst is None:
                continue
            label = f"Connection '{conn.name}'  ({conn.from_} ↔ {conn.to})"
            node = ConnectionNode(conn, label)
            key = _key_for_connection(conn.name)
            if key in self._cached_road_positions:
                node.setPos(self._cached_road_positions[key])
            else:
                node.setPos(QPointF((src.x() + dst.x()) / 2.0, (src.y() + dst.y()) / 2.0))
            self.addItem(node)
            connection_nodes[conn.name] = node
            self._road_connection_items[key] = node

        # Roads — resolve each anchor to a node and draw the edge.
        for zone in variant.zones:
            mo_nodes = zone_main_nodes.get(zone.name, [])
            content_nodes = zone_content_nodes.get(zone.name, {})
            for road in zone.roads or []:
                src_node = self._resolve_anchor_node(
                    road.from_, mo_nodes, content_nodes, connection_nodes
                )
                dst_node = self._resolve_anchor_node(
                    road.to, mo_nodes, content_nodes, connection_nodes
                )
                if src_node is None or dst_node is None or src_node is dst_node:
                    continue
                tooltip = _road_tooltip(zone.name, road)
                self.addItem(RoadEdgeItem(road, src_node, dst_node, tooltip))

    def _resolve_anchor_node(
        self,
        anchor: Anchor,
        mo_nodes: list[ObjectNode],
        content_nodes: dict[str, ObjectNode],
        connection_nodes: dict[str, ConnectionNode],
    ) -> ObjectNode | ConnectionNode | None:
        if not anchor.args:
            return None
        first = anchor.args[0]
        if anchor.type == "MainObject":
            try:
                idx = int(first)
            except (TypeError, ValueError):
                return None
            if 0 <= idx < len(mo_nodes):
                return mo_nodes[idx]
            return None
        if anchor.type == "Connection":
            return connection_nodes.get(str(first))
        if anchor.type == "MandatoryContent":
            return content_nodes.get(str(first))
        return None

    # ── Shared callbacks ──────────────────────────────────────────────────

    def _forward_selection(self) -> None:
        items = self.selectedItems()
        target = getattr(items[0], "model_target", None) if items else None
        self._session.set_selection(target)

    def _refresh_for(self, obj: object) -> None:
        if isinstance(obj, Variant) and obj is self.current_variant:
            self.rebuild()
            return
        if self._show_roads:
            # The road graph derives from zone.roads / zone.mainObjects /
            # zone.mandatoryContent and variant.connections; any zone change in the
            # current variant can shift nodes or edges, so rebuild from scratch.
            variant = self.current_variant
            if isinstance(obj, Zone) and variant is not None and any(z is obj for z in variant.zones):
                self.rebuild()
                return
        else:
            if isinstance(obj, Zone) and obj.name in self._zone_items:
                self._zone_items[obj.name].refresh()
                self._restyle_zones()
                return
            if self._is_in_current_variant_zone(obj):
                self._restyle_zones()
                return
        for item in self.items():
            if getattr(item, "model_target", None) is obj:
                refresh = getattr(item, "refresh", None)
                if callable(refresh):
                    refresh()
                return

    def _restyle_zones(self) -> None:
        variant = self.current_variant
        if variant is None:
            return
        styles = compute_zone_styles(variant)
        for name, item in self._zone_items.items():
            style = styles.get(name)
            if style is not None:
                item.update_style(style.radius, style.fill)

    def _is_in_current_variant_zone(self, obj: object) -> bool:
        variant = self.current_variant
        if variant is None:
            return False
        for zone in variant.zones:
            for mo in zone.mainObjects:
                if mo is obj:
                    return True
        return False


# ── Helpers ───────────────────────────────────────────────────────────────


def _fan_offset(index: int, total: int) -> QPointF:
    if total <= 1:
        return QPointF(0.0, 0.0)
    angle = 2.0 * math.pi * index / total - math.pi / 2.0
    return QPointF(
        _OBJECT_FAN_RADIUS * math.cos(angle),
        _OBJECT_FAN_RADIUS * math.sin(angle),
    )


def _key_for_main_object(zone_name: str, index: int) -> str:
    return f"mo:{zone_name}:{index}"


def _key_for_content_item(zone_name: str, item_name: str | None) -> str | None:
    if item_name is None:
        return None
    return f"ci:{zone_name}:{item_name}"


def _key_for_connection(conn_name: str) -> str:
    return f"conn:{conn_name}"


_MAIN_OBJECT_TYPES = (
    SpawnObject,
    CityObject,
    AbandonedOutpostObject,
    GladiatorArenaObject,
    EmptyMainObject,
)
_CONNECTION_TYPES = (
    DirectConnection,
    DefaultConnection,
    PortalConnection,
    ProximityConnection,
    GladiatorArenaConnection,
)


def _zone_by_name(name: str, variant: Variant) -> Zone | None:
    for zone in variant.zones:
        if zone.name == name:
            return zone
    return None


def _zones_containing_node(target: object, variant: Variant, template: object) -> set[str]:
    """Return the names of zones in which this model object can act as a road endpoint."""
    if isinstance(target, _MAIN_OBJECT_TYPES):
        return {zone.name for zone in variant.zones if any(mo is target for mo in zone.mainObjects)}
    if isinstance(target, _CONNECTION_TYPES):
        return {zone.name for zone in variant.zones if zone.name in (target.from_, target.to)}
    if isinstance(target, ContentItemRuntime):
        bundle_names: set[str] = set()
        for bundle in template.mandatoryContent:  # type: ignore[attr-defined]
            if any(ci is target for ci in bundle.content):
                bundle_names.add(bundle.name)
        if not bundle_names:
            return set()
        return {
            zone.name
            for zone in variant.zones
            if any(b in bundle_names for b in (zone.mandatoryContent or []))
        }
    return set()


def _anchor_for_in_zone(target: object, zone: Zone, template: object) -> AnchorRuntime | None:
    if isinstance(target, _MAIN_OBJECT_TYPES):
        for i, mo in enumerate(zone.mainObjects):
            if mo is target:
                return AnchorRuntime(type="MainObject", args=[str(i)])
        return None
    if isinstance(target, _CONNECTION_TYPES):
        if target.name is None:
            return None
        return AnchorRuntime(type="Connection", args=[target.name])
    if isinstance(target, ContentItemRuntime):
        if target.name is None:
            return None
        # Confirm the bundle containing `target` is actually referenced by this zone.
        for bundle in template.mandatoryContent:  # type: ignore[attr-defined]
            if any(ci is target for ci in bundle.content):
                if bundle.name in (zone.mandatoryContent or []):
                    return AnchorRuntime(type="MandatoryContent", args=[target.name])
                return None
        return None
    return None


def _content_anchor_refs(zone: Zone) -> set[str]:
    """Names referenced by `MandatoryContent` road anchors in this zone."""
    refs: set[str] = set()
    for road in zone.roads or []:
        for anchor in (road.from_, road.to):
            if anchor.type == "MandatoryContent" and anchor.args:
                refs.add(str(anchor.args[0]))
    return refs


def _resolvable_content_items(
    zone: Zone,
    bundle_by_name: dict[str, object],
    referenced: set[str],
    show_all: bool,
) -> list[ContentItem]:
    """Walk the zone's mandatoryContent bundles for ContentItems we want to render.

    Default mode emits only items whose `name` is referenced by some road anchor
    in this zone (so unnamed items, which can't be road-targeted, are skipped).
    `show_all=True` emits every item from the referenced bundles, including the
    unnamed ones — they appear as draggable nodes so the user can see what the
    bundle contains, but only named items get registered for road resolution."""
    out: list[ContentItem] = []
    seen_names: set[str] = set()
    for bundle_name in zone.mandatoryContent or []:
        bundle = bundle_by_name.get(bundle_name)
        if bundle is None:
            continue
        for item in bundle.content:  # type: ignore[attr-defined]
            if not show_all and (item.name is None or item.name not in referenced):
                continue
            if item.name is not None:
                if item.name in seen_names:
                    continue
                seen_names.add(item.name)
            out.append(item)
    return out


def _content_node_for(
    item: ContentItem, zone: Zone, catalog: GameDataCatalog | None
) -> ObjectNode:
    from PySide6.QtGui import QColor

    label = f"'{zone.name}' / {item.name} ({item.sid})"
    icon: QIcon | None = None
    if catalog is not None and item.sid is not None:
        from templategen.ui.asset_icons import sid_listable

        icon = sid_listable(catalog, item.sid).icon
    glyph = None
    if icon is None and item.sid:
        glyph = item.sid[:1].upper()
    return ObjectNode(item, label, icon=icon, fill=QColor("#3d3a2f"), glyph=glyph)


def _object_node_for(mo: object, zone: Zone, index: int) -> ObjectNode:
    from PySide6.QtGui import QColor

    label_prefix = f"'{zone.name}' / MainObject[{index}]"
    if isinstance(mo, SpawnObject):
        spawn = getattr(mo, "spawn", None) or getattr(mo, "owner", None)
        fill = _PLAYER_COLOR.get(spawn, QColor("#a358cf")) if spawn else QColor("#888")
        glyph = _player_glyph(spawn)
        return ObjectNode(mo, f"{label_prefix} — Spawn ({spawn or 'unassigned'})",
                          fill=fill, glyph=glyph)
    if isinstance(mo, CityObject):
        icon = _faction_icon(mo)
        factions = ", ".join(mo.factions or []) or "any faction"
        return ObjectNode(mo, f"{label_prefix} — City ({factions})",
                          icon=icon, fill=QColor("#3c4252"), glyph="C" if icon is None else None)
    if isinstance(mo, GladiatorArenaObject):
        return ObjectNode(mo, f"{label_prefix} — Gladiator Arena",
                          fill=QColor("#5a2f2f"), glyph="G")
    if isinstance(mo, EmptyMainObject):
        return ObjectNode(mo, f"{label_prefix} — (empty)",
                          fill=QColor("#3a3a3e"), glyph="·")
    # AbandonedOutpostObject + fallback for any future _MainObjectBase subtype.
    kind = getattr(getattr(mo, "type", None), "value", "Object")
    glyph = "A" if kind == MainObjectType.ABANDONED_OUTPOST.value else "?"
    return ObjectNode(mo, f"{label_prefix} — {kind}",
                      fill=QColor("#5a4a2a"), glyph=glyph)


def _faction_icon(mo: CityObject) -> QIcon | None:
    if not mo.factions:
        return None
    from templategen.ui.asset_icons import fraction_qicon

    for fac in mo.factions:
        icon = fraction_qicon(fac)
        if icon is not None and not icon.isNull():
            return icon
    return None


def _player_glyph(spawn: str | None) -> str:
    if not spawn:
        return "S"
    digits = "".join(ch for ch in spawn if ch.isdigit())
    return digits or "S"


def _road_tooltip(zone_name: str, road: object) -> str:
    def fmt(anchor: object) -> str:
        atype = getattr(anchor, "type", "?")
        args = getattr(anchor, "args", [])
        return f"{atype}({', '.join(str(a) for a in args)})"

    rtype = getattr(road, "type", None)
    prefix = f"{rtype.value} road" if rtype is not None else "Road"
    return f"{prefix} in '{zone_name}': {fmt(road.from_)} → {fmt(road.to)}"  # type: ignore[attr-defined]


def _parallel_offsets(connections: list[object]) -> dict[int, float]:
    """Compute a per-edge perpendicular offset for groups of parallel connections.

    Connections in the same unordered (from, to) group share a fanout. Each connection's
    perpendicular vector flips when its from_/to are swapped, so the offset sign must
    flip too — otherwise A→B and B→A would land on opposite sides of the centerline
    instead of fanning out together.
    """
    groups: dict[frozenset[str], list[object]] = {}
    for conn in connections:
        key = frozenset({conn.from_, conn.to})  # type: ignore[attr-defined]
        groups.setdefault(key, []).append(conn)

    offsets: dict[int, float] = {}
    for key, group in groups.items():
        n = len(group)
        if n == 1:
            offsets[id(group[0])] = 0.0
            continue
        canonical = sorted(key)
        canonical_from = canonical[0] if canonical else None
        is_self_loop = len(canonical) < 2
        for i, conn in enumerate(group):
            base = (i - (n - 1) / 2.0) * _PARALLEL_SPACING
            sign = 1.0 if is_self_loop or conn.from_ == canonical_from else -1.0  # type: ignore[attr-defined]
            offsets[id(conn)] = base * sign
    return offsets
