"""MainObject — discriminated union over the four placeable types, plus the empty `{}` slot."""

from typing import Annotated, Any, Literal

from pydantic import Discriminator, Tag

from templategen.model.base import RmgModel
from templategen.model.enums import MainObjectType, Placement, PlayerId
from templategen.model.selectors import FactionSelector


class _MainObjectBase(RmgModel):
    placement: Placement | None = None
    placementArgs: list[str] | None = None
    guardChance: float | None = None
    guardValue: int | None = None
    guardWeeklyIncrement: float | None = None
    guardRandomization: float | None = None
    removeGuardIfHasOwner: bool | None = None
    buildingsConstructionSid: str | None = None
    faction: FactionSelector | None = None
    factions: list[str] | None = None
    owner: PlayerId | None = None
    isKeyObject: bool | None = None
    holdCityWinCon: bool | None = None
    enableWeeklyUnitIncrement: bool | None = None
    initialUnitIncrement: float | None = None


class SpawnObject(_MainObjectBase):
    type: Literal[MainObjectType.SPAWN] = MainObjectType.SPAWN
    spawn: PlayerId | None = None


class CityObject(_MainObjectBase):
    type: Literal[MainObjectType.CITY] = MainObjectType.CITY


class AbandonedOutpostObject(_MainObjectBase):
    type: Literal[MainObjectType.ABANDONED_OUTPOST] = MainObjectType.ABANDONED_OUTPOST


class GladiatorArenaObject(_MainObjectBase):
    type: Literal[MainObjectType.GLADIATOR_ARENA] = MainObjectType.GLADIATOR_ARENA


class EmptyMainObject(RmgModel):
    """The `{}` placeholder some templates use for a "no real main object" slot."""


def _discriminate(value: Any) -> str:
    if isinstance(value, dict):
        return value.get("type") or "Empty"
    return getattr(value, "type", None) or "Empty"


MainObject = Annotated[
    Annotated[SpawnObject, Tag(MainObjectType.SPAWN.value)]
    | Annotated[CityObject, Tag(MainObjectType.CITY.value)]
    | Annotated[AbandonedOutpostObject, Tag(MainObjectType.ABANDONED_OUTPOST.value)]
    | Annotated[GladiatorArenaObject, Tag(MainObjectType.GLADIATOR_ARENA.value)]
    | Annotated[EmptyMainObject, Tag("Empty")],
    Discriminator(_discriminate),
]
