"""Placement rules, anchors, mandatory content bundles, and count limits."""

from typing import Any

from templategen.model.base import RmgModel
from templategen.model.enums import PlayerId


class Anchor(RmgModel):
    type: str
    args: list[Any] = []


class PlacementRule(RmgModel):
    type: str
    args: list[Any] = []
    targetMin: float | None = None
    targetMax: float | None = None
    target: float | None = None
    weight: float | None = None


class ContentItem(RmgModel):
    sid: str | None = None
    variant: int | None = None
    name: str | None = None
    isMine: bool | None = None
    isGuarded: bool | None = None
    soloEncounter: bool | None = None
    designatedEncounter: bool | None = None
    road: bool | None = None
    owner: PlayerId | None = None
    guardValue: int | None = None
    rules: list[PlacementRule] | None = None
    includeLists: list[str] | None = None


class MandatoryContentBundle(RmgModel):
    name: str
    content: list[ContentItem] = []


class LimitItem(RmgModel):
    sid: str | None = None
    variant: int | None = None
    maxCount: int
    includeLists: list[str] | None = None
    content: list[ContentItem] | None = None


class ContentCountLimit(RmgModel):
    name: str
    limits: list[LimitItem] = []
