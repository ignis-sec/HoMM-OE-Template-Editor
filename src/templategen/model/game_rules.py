"""Game rules, win conditions, bonuses, bans, and per-object value overrides."""

from pydantic import BaseModel


class WinConditions(BaseModel): ...


class Bonus(BaseModel): ...


class GlobalBans(BaseModel): ...


class ValueOverride(BaseModel): ...


class GameRules(BaseModel): ...
