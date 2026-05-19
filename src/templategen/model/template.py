"""Template — the root .rmg.json document."""

from templategen.model.base import RmgModel
from templategen.model.content import ContentCountLimit, MandatoryContentBundle
from templategen.model.enums import GameMode
from templategen.model.game_rules import GameRules, GlobalBans, ValueOverride
from templategen.model.layouts import ZoneLayout
from templategen.model.variant import Variant


class Template(RmgModel):
    name: str
    description: str | None = None
    displayWinCondition: str | None = None
    gameMode: GameMode
    sizeX: int
    sizeZ: int

    gameRules: GameRules
    globalBans: GlobalBans | None = None
    valueOverrides: list[ValueOverride] | None = None

    variants: list[Variant] = []
    zoneLayouts: list[ZoneLayout] = []
    mandatoryContent: list[MandatoryContentBundle] = []
    contentCountLimits: list[ContentCountLimit] = []
    contentPools: list[object] = []
    contentLists: list[object] = []
