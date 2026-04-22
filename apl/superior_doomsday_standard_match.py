"""apl/superior_doomsday_standard_match.py -- Superior Doomsday match APL.

Thin wrapper — delegates to the goldfish APL's ControlAPL turn loop.
"""
from apl.match_apl import MatchAPL
from apl.superior_doomsday_standard import (
    SuperiorDoomsdayAPL,
    INTIMIDATION, BITTER, REQUITING, COVER_UP,
    DECEIT, HARVESTER, SPIDER_MAN, EXCRUCIATOR, MALBORO,
    STOCK_UP, WINTERNIGHT, AVARICE, CHARM,
)


class SuperiorDoomsdayStandardMatchAPL(MatchAPL):
    name = "Superior Doomsday"
    win_condition_damage = 20
    max_turns = 15

    HAND_ATTACK = (INTIMIDATION,)
    REMOVAL = (REQUITING, BITTER)
    COUNTERS = ()
    WIPES = (COVER_UP,)
    THREATS = (SPIDER_MAN, DECEIT, HARVESTER, MALBORO, EXCRUCIATOR)
    VALUE_SPELLS = (AVARICE, STOCK_UP, WINTERNIGHT, CHARM)

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        threats = sum(1 for c in hand if c.name in self.THREATS)
        answers = sum(1 for c in hand if c.name in self.REMOVAL + self.WIPES)
        if lands < 2 or lands > 6:
            return False
        if threats + answers >= 2:
            return True
        return mulligans >= 2

    def bottom(self, hand, n):
        lands = [c for c in hand if c.is_land()]
        if len(lands) > 4:
            return lands[4:][:n]
        return lands[4:][:n]

    def main_phase(self, gs):
        SuperiorDoomsdayAPL.main_phase(self, gs)

    def main_phase2(self, gs):
        SuperiorDoomsdayAPL.main_phase2(self, gs)
