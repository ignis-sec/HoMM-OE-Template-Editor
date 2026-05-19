"""Connection hierarchy — edges in the zone graph."""

from pydantic import BaseModel


class Connection(BaseModel): ...


class DirectConnection(Connection): ...


class DefaultConnection(Connection): ...


class PortalConnection(Connection): ...


class ProximityConnection(Connection): ...


class GladiatorArenaConnection(Connection): ...
