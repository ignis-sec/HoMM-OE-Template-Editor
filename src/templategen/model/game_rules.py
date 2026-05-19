"""Game rules, win conditions, bonuses, bans, and per-object value overrides."""

from templategen.model.base import RmgModel


class WinConditions(RmgModel):
    classic: bool | None = None
    desertion: bool | None = None
    desertionDay: int | None = None
    desertionValue: int | None = None
    heroLighting: bool | None = None
    heroLightingDay: int | None = None
    lostStartCity: bool | None = None
    lostStartCityDay: int | None = None
    lostStartHero: bool | None = None
    cityHold: bool | None = None
    cityHoldDays: int | None = None
    gladiatorArena: bool | None = None
    gladiatorArenaRegistrationStartWork: bool | None = None
    gladiatorArenaRegistrationStartFight: bool | None = None
    gladiatorArenaDaysDelayStart: int | None = None
    gladiatorArenaCountDay: int | None = None
    championSelectRule: str | None = None
    tournament: bool | None = None
    tournamentSaveArmy: bool | None = None
    tournamentAnnounceDays: int | list[int] | None = None
    tournamentDays: int | list[int] | None = None
    tournamentPointsToWin: int | None = None
    encounterHoles: bool | None = None
    holdCityWinCon: bool | None = None


class Bonus(RmgModel):
    sid: str
    receiverSide: int | None = None
    receiverFilter: str | None = None
    parameters: list[str] = []


class GlobalBans(RmgModel):
    magics: list[str] | None = None
    items: list[str] | None = None


class ValueOverride(RmgModel):
    sid: str
    variant: int | None = None
    guardValue: int | None = None


class GameRules(RmgModel):
    heroCountMin: int | None = None
    heroCountMax: int | None = None
    heroCountIncrement: int | None = None
    heroHireBan: bool | None = None
    encounterHoles: bool | None = None
    winConditions: WinConditions | None = None
    bonuses: Bonus | list[Bonus] | None = None
    factionLawsExpModifier: float | None = None
    astrologyExpModifier: float | None = None
    globalBans: GlobalBans | None = None
    valueOverrides: list[ValueOverride] | None = None
    championSelectRule: str | None = None
