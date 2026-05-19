"""Reusable zone layout presets."""

from templategen.model.base import RmgModel


class ElevationMode(RmgModel):
    weight: float
    minElevatedFraction: float
    maxElevatedFraction: float


class GuardedEncounterResourceFractions(RmgModel):
    countBounds: list[int] = []
    fractions: list[float] = []


class AmbientPickupDistribution(RmgModel):
    repulsion: float | None = None
    noise: float | None = None
    roadAttraction: float | None = None
    obstacleAttraction: float | None = None
    groupSizeWeights: list[int] | None = None


class ZoneLayout(RmgModel):
    name: str
    obstaclesFill: float | None = None
    obstaclesFillVoid: float | None = None
    lakesFill: float | None = None
    minLakeArea: int | None = None
    elevationClusterScale: float | None = None
    elevationModes: list[ElevationMode] | None = None
    roadClusterArea: int | None = None
    guardedEncounterResourceFractions: GuardedEncounterResourceFractions | None = None
    ambientPickupDistribution: AmbientPickupDistribution | None = None
