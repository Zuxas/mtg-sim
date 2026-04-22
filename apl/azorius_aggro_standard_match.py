"""apl/azorius_aggro_standard_match.py -- Azorius Merfolk match APL."""
from apl.match_apl import MatchAPL
from apl.azorius_aggro_standard import (
    AzoriusAggroAPL,
    WANDERBRINE, DEEPCHANNEL, DEEPWAY, SILVERGILL, FLOODPITS,
    MINDSPRING, TIDEBINDER, DISRUPTOR,
    SYGGS_CMD, THREE_STEPS,
)


class AzoriusAggroStandardMatchAPL(MatchAPL):
    name = "Azorius Aggro"
    win_condition_damage = 20
    max_turns = 12

    CREATURES = (MINDSPRING, WANDERBRINE, DEEPCHANNEL, DEEPWAY, SILVERGILL,
                  FLOODPITS, TIDEBINDER, DISRUPTOR)
    CANTRIP_SPELLS = (SYGGS_CMD, THREE_STEPS)
    BURN_SPELLS = {}
    PUMP_SPELLS = {}
    HASTE_CREATURES = frozenset()

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        threats = sum(1 for c in hand if c.name in self.CREATURES)
        if lands < 2 or lands > 4:
            return False
        if threats >= 2:
            return True
        return mulligans >= 2

    def bottom(self, hand, n):
        lands = [c for c in hand if c.is_land()]
        return lands[2:][:n]

    def main_phase(self, gs):
        AzoriusAggroAPL.main_phase(self, gs)

    def main_phase2(self, gs):
        AzoriusAggroAPL.main_phase2(self, gs)
