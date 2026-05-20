"""Connection — discriminated union over the five connection kinds."""

from typing import Annotated, Literal

from pydantic import Field

from templategen.model.base import RmgModel
from templategen.model.content import PlacementRule
from templategen.model.enums import ConnectionType


class _ConnectionBase(RmgModel):
    name: str | None = None
    from_: str = Field(alias="from")
    to: str
    road: bool | None = None
    guardZone: str | None = None
    guardEscape: bool | None = None
    guardValue: int | None = None
    guardWeeklyIncrement: float | None = None
    guardRandomization: float | None = None
    guardMatchGroup: str | None = None
    simTurnSquad: bool | None = None
    gatePlacement: str | None = None

    def model_post_init(self, __context: object) -> None:
        self.__pydantic_fields_set__.add("connectionType")


class DirectConnection(_ConnectionBase):
    connectionType: Literal[ConnectionType.DIRECT] = ConnectionType.DIRECT


class DefaultConnection(_ConnectionBase):
    connectionType: Literal[ConnectionType.DEFAULT] = ConnectionType.DEFAULT


class PortalConnection(_ConnectionBase):
    connectionType: Literal[ConnectionType.PORTAL] = ConnectionType.PORTAL
    portalPlacementRulesFrom: list[PlacementRule] | None = None
    portalPlacementRulesTo: list[PlacementRule] | None = None


class ProximityConnection(_ConnectionBase):
    connectionType: Literal[ConnectionType.PROXIMITY] = ConnectionType.PROXIMITY
    length: float | None = None


class GladiatorArenaConnection(_ConnectionBase):
    connectionType: Literal[ConnectionType.GLADIATOR_ARENA] = ConnectionType.GLADIATOR_ARENA


Connection = Annotated[
    DirectConnection | DefaultConnection | PortalConnection | ProximityConnection | GladiatorArenaConnection,
    Field(discriminator="connectionType"),
]
