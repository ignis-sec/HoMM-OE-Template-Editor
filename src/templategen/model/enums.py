"""Enumerations used across the template schema."""

from enum import StrEnum


class GameMode(StrEnum):
    CLASSIC = "Classic"
    SINGLE_HERO = "SingleHero"


class OrientationMode(StrEnum):
    MINIMAL_BOUNDING_SQUARE = "MinimalBoundingSquare"
    BOUNDING_CIRCLE = "BoundingCircle"


class MainObjectType(StrEnum):
    SPAWN = "Spawn"
    CITY = "City"
    ABANDONED_OUTPOST = "AbandonedOutpost"
    GLADIATOR_ARENA = "GladiatorArena"


class ConnectionType(StrEnum):
    DIRECT = "Direct"
    DEFAULT = "Default"
    PORTAL = "Portal"
    PROXIMITY = "Proximity"
    GLADIATOR_ARENA = "GladiatorArena"


class Placement(StrEnum):
    CENTER = "Center"
    UNIFORM = "Uniform"
    CONNECTION = "Connection"
    NEAR_ZONE = "NearZone"


class RoadType(StrEnum):
    STONE = "Stone"
    DIRT = "Dirt"


class PlayerId(StrEnum):
    PLAYER_1 = "Player1"
    PLAYER_2 = "Player2"
    PLAYER_3 = "Player3"
    PLAYER_4 = "Player4"
    PLAYER_5 = "Player5"
    PLAYER_6 = "Player6"
    PLAYER_7 = "Player7"
    PLAYER_8 = "Player8"


class RuleAnchorType(StrEnum):
    MAIN_OBJECT = "MainObject"
    CONNECTION = "Connection"
    CROSSROADS = "Crossroads"
    ROAD = "Road"
    SID = "Sid"
    MANDATORY_CONTENT = "MandatoryContent"
