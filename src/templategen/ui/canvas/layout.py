"""Deterministic 2D placement for a Variant's zones."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

import networkx as nx

from templategen.model.enums import ConnectionType

if TYPE_CHECKING:
    from templategen.model.variant import Variant

_LAYOUT_SEED: Final[int] = 42
_SPRING_ITERATIONS: Final[int] = 200
_COMPONENT_GAP: Final[float] = 1.0  # in normalized layout units

Position = tuple[float, float]


def compute_layout(variant: Variant) -> dict[str, Position]:
    graph = _build_graph(variant)
    if graph.number_of_nodes() <= 1:
        return dict.fromkeys(graph.nodes, (0.0, 0.0))

    # Lay each connected component out on its own, then pack the components
    # side by side. Otherwise multi-graph templates (Sprint, Exodus) collapse
    # all components onto the same Kamada-Kawai centroid and overlap.
    components = sorted(
        (sorted(c) for c in nx.connected_components(graph)),
        key=lambda c: (-len(c), c[0] if c else ""),
    )
    if len(components) == 1:
        return _center(_to_tuples(_layout_subgraph(graph)))
    return _pack_components([_layout_subgraph(graph.subgraph(comp)) for comp in components])


def _layout_subgraph(graph: nx.Graph) -> dict[str, Position]:
    if graph.number_of_nodes() == 0:
        return {}
    if graph.number_of_nodes() == 1:
        return {next(iter(graph.nodes)): (0.0, 0.0)}
    try:
        raw = nx.kamada_kawai_layout(graph)
    except (nx.NetworkXError, ValueError, ImportError):
        raw = nx.spring_layout(graph, seed=_LAYOUT_SEED, iterations=_SPRING_ITERATIONS)
    return _to_tuples(raw)


def _pack_components(layouts: list[dict[str, Position]]) -> dict[str, Position]:
    """Place each component's bounding box side by side with a gap, vertically
    centered, then center the union on the origin."""
    out: dict[str, Position] = {}
    cursor = 0.0
    for comp in layouts:
        if not comp:
            continue
        xs = [p[0] for p in comp.values()]
        ys = [p[1] for p in comp.values()]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        cy = (min_y + max_y) / 2.0
        shift_x = cursor - min_x
        shift_y = -cy
        for name, (x, y) in comp.items():
            out[name] = (x + shift_x, y + shift_y)
        cursor += (max_x - min_x) + _COMPONENT_GAP
    return _center(out)


def _build_graph(variant: Variant) -> nx.Graph:
    graph = nx.Graph()
    for zone in variant.zones:
        graph.add_node(zone.name)
    for conn in variant.connections:
        if conn.connectionType == ConnectionType.PROXIMITY:
            continue
        graph.add_edge(conn.from_, conn.to)
    return graph


def _to_tuples(raw: dict[str, object]) -> dict[str, Position]:
    return {name: (float(pos[0]), float(pos[1])) for name, pos in raw.items()}


def _center(positions: dict[str, Position]) -> dict[str, Position]:
    if not positions:
        return positions
    cx = sum(p[0] for p in positions.values()) / len(positions)
    cy = sum(p[1] for p in positions.values()) / len(positions)
    return {name: (p[0] - cx, p[1] - cy) for name, p in positions.items()}
