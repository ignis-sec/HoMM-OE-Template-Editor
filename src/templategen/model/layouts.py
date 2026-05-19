"""Reusable zone layout presets referenced by zones."""

from pydantic import BaseModel


class ElevationMode(BaseModel): ...


class GuardedEncounterResourceFractions(BaseModel): ...


class AmbientPickupDistribution(BaseModel): ...


class ZoneLayout(BaseModel): ...
