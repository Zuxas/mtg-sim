"""apl/izzet_prowess_standard_match.py -- Izzet Prowess match APL.

Thin wrapper over the goldfish APL so the analyzer's Standard
discovery picks this archetype up.
"""
from apl.match_apl import MatchAPL
from apl.izzet_prowess_standard import (
    IzzetProwessAPL,
    ELUSIVE_OTTER, SLICKSHOT, STORMCHASER, EDDYMURK,
    OPT, SLEIGHT, STOCK_UP, BOUNCE, BOOMERANG,
    BURST, WILD_RIDE,
)


class IzzetProwessStandardMatchAPL(MatchAPL):
    name = "Izzet Prowess"
    win_condition_damage = 20
    max_turns = 12

    CREATURES = (ELUSIVE_OTTER, SLICKSHOT, STORMCHASER, EDDYMURK)
    CANTRIP_SPELLS = (OPT, SLEIGHT, STOCK_UP, BOUNCE, BOOMERANG)
    BURN_SPELLS = {BURST: (1, 2)}
    PUMP_SPELLS = {WILD_RIDE: (1, 3, False)}
    HASTE_CREATURES = frozenset({SLICKSHOT})

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        threats = sum(1 for c in hand if c.name in self.CREATURES)
        cantrips = sum(1 for c in hand if c.name in self.CANTRIP_SPELLS)
        if lands < 2 or lands > 4:
            return False
        if threats + cantrips >= 3:
            return True
        return mulligans >= 2

    def bottom(self, hand, n):
        lands = [c for c in hand if c.is_land()]
        if len(lands) > 3:
            return lands[3:][:n]
        return lands[3:][:n]

    def main_phase(self, gs):
        IzzetProwessAPL.main_phase(self, gs)

    def main_phase2(self, gs):
        IzzetProwessAPL.main_phase2(self, gs)
