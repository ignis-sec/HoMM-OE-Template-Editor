"""Faction and biome selectors — polymorphic by `type` discriminator."""

from pydantic import BaseModel


class FactionSelector(BaseModel): ...


class FromListFactionSelector(FactionSelector): ...


class MatchFactionSelector(FactionSelector): ...


class BiomeSelector(BaseModel): ...


class FromListBiomeSelector(BiomeSelector): ...


class MatchBiomeSelector(BiomeSelector): ...


class MatchMainObjectBiomeSelector(BiomeSelector): ...


class MatchZoneBiomeSelector(BiomeSelector): ...
