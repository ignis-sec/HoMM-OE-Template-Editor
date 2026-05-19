"""Deterministic 2D placement for a Variant's zones."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

import networkx as nx

from templategen.model.enums import ConnectionType

if TYPE_CHECKING:
    from templategen.model.variant import Variant

_LAYOUT_SEED: Final[int] = 42
_SPRING_ITERATIONS: Final[int] = 200

Position = tuple[float, float]


def compute_layout(variant: Variant) -> dict[str, Position]:
    graph = _build_graph(variant)
    if graph.number_of_nodes() <= 1:
        return dict.fromkeys(graph.nodes, (0.0, 0.0))

    try:
        raw = nx.kamada_kawai_layout(graph)
    except (nx.NetworkXError, ValueError, ImportError):
        raw = nx.spring_layout(graph, seed=_LAYOUT_SEED, iterations=_SPRING_ITERATIONS)
    return _center(_to_tuples(raw))


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
