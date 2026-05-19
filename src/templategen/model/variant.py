"""Variant — one of the alternative zone graphs a template may pick at generation time."""

from templategen.model.base import RmgModel
from templategen.model.connection import Connection
from templategen.model.enums import OrientationMode
from templategen.model.zone import Zone


class NoiseLayer(RmgModel):
    amp: float
    freq: float


class Border(RmgModel):
    cornerRadius: float | None = None
    obstaclesWidth: int | None = None
    obstaclesNoise: list[NoiseLayer] | None = None
    waterWidth: int | None = None
    waterNoise: list[NoiseLayer] | None = None
    waterType: str | None = None


class Orientation(RmgModel):
    mode: OrientationMode | None = None
    zeroAngleZone: str | None = None
    baseAngleMin: float | None = None
    baseAngleMax: float | None = None
    randomAngleAmplitude: float | None = None
    randomAngleStep: float | None = None


class Variant(RmgModel):
    orientation: Orientation
    border: Border | None = None
    zones: list[Zone] = []
    connections: list[Connection] = []
