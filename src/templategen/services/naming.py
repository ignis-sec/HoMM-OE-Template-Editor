"""Name-generation helpers — keep auto-generated names unique within a collection."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

    from templategen.model.variant import Variant


def unique_name(base: str, existing: Iterable[str]) -> str:
    taken = set(existing)
    if base not in taken:
        return base
    i = 1
    while f"{base}_{i}" in taken:
        i += 1
    return f"{base}_{i}"


def unique_zone_name(variant: Variant, base: str = "Zone") -> str:
    return unique_name(base, (z.name for z in variant.zones))


def unique_connection_name(variant: Variant, from_: str, to: str) -> str:
    base = f"{from_}_{to}"
    return unique_name(base, (c.name for c in variant.connections if c.name))
