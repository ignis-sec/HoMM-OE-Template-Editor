"""Zone — a node in a Variant's graph, plus the internal Road segments."""

from pydantic import Field

from templategen.model.base import RmgModel
from templategen.model.content import Anchor
from templategen.model.enums import RoadType
from templategen.model.main_objects import MainObject
from templategen.model.selectors import BiomeSelector


class Road(RmgModel):
    type: RoadType | None = None
    from_: Anchor = Field(alias="from")
    to: Anchor


class EncounterHolesSettings(RmgModel):
    affectedEncounters: float | None = None
    twoHoleEncounters: float | None = None


class Zone(RmgModel):
    name: str
    size: float
    layout: str

    guardCutoffValue: int | None = None
    guardRandomization: float | None = None
    guardMultiplier: float | None = None
    guardWeeklyIncrement: float | None = None
    guardReactionDistribution: list[int] | None = None
    diplomacyModifier: float | None = None

    guardedContentPool: list[str] | None = None
    unguardedContentPool: list[str] | None = None
    resourcesContentPool: list[str] | None = None

    mandatoryContent: list[str] | None = None
    contentCountLimits: str | list[str] | None = None

    guardedContentValue: int | None = None
    guardedContentValuePerArea: int | None = None
    unguardedContentValue: int | None = None
    unguardedContentValuePerArea: int | None = None
    resourcesValue: int | None = None
    resourcesValuePerArea: int | None = None

    mainObjects: list[MainObject] = []

    zoneBiome: BiomeSelector | None = None
    contentBiome: BiomeSelector | None = None
    metaObjectsBiome: BiomeSelector | None = None

    crossroadsPosition: int | None = None
    roads: list[Road] | None = None

    encounterHolesSettings: EncounterHolesSettings | None = None
    randomHireInitialUnitIncrement: list[float] | None = None
    randomHireEnableWeeklyUnitIncrement: list[bool] | None = None
