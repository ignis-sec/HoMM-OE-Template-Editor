"""MainObject hierarchy — objects guaranteed to appear inside a zone."""

from pydantic import BaseModel


class MainObject(BaseModel): ...


class SpawnObject(MainObject): ...


class CityObject(MainObject): ...


class AbandonedOutpostObject(MainObject): ...


class GladiatorArenaObject(MainObject): ...
