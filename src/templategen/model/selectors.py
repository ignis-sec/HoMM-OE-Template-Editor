"""Faction and biome selectors — { type, args } shape."""

from typing import Any

from templategen.model.base import RmgModel


class FactionSelector(RmgModel):
    type: str
    args: list[Any] = []


class BiomeSelector(RmgModel):
    type: str
    args: list[Any] = []
