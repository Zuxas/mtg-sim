"""apl/izzet_spellementals_standard_match.py -- Spellementals match APL."""
from apl.match_apl import MatchAPL
from apl.izzet_spellementals_standard import (
    IzzetSpellementalsAPL,
    SPELL_PIERCE, SPELL_SNARE, ABRADE, SEAR,
    ABANDON, BOUNCE, BURST,
    HEARTH, EDDY, SUNDER,
    OPT, SLEIGHT, WINTERNIGHT, DRAGONHUNT,
)


class IzzetSpellementalsStandardMatchAPL(MatchAPL):
    name = "Izzet Spellementals"
    win_condition_damage = 20
    max_turns = 15

    HAND_ATTACK = (ABANDON, BOUNCE)
    REMOVAL = (SPELL_PIERCE, SPELL_SNARE, ABRADE, SEAR)
    COUNTERS = (SPELL_PIERCE, SPELL_SNARE)
    WIPES = ()
    THREATS = (HEARTH, EDDY, SUNDER)
    VALUE_SPELLS = (OPT, SLEIGHT, WINTERNIGHT, DRAGONHUNT, BURST)

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        cantrips = sum(1 for c in hand if c.name in self.VALUE_SPELLS)
        threats = sum(1 for c in hand if c.name in self.THREATS)
        answers = sum(1 for c in hand if c.name in self.REMOVAL)
        if lands < 2 or lands > 5:
            return False
        if cantrips + answers >= 2 or threats >= 1:
            return True
        return mulligans >= 2

    def bottom(self, hand, n):
        lands = [c for c in hand if c.is_land()]
        return lands[3:][:n]

    def main_phase(self, gs):
        IzzetSpellementalsAPL.main_phase(self, gs)

    def main_phase2(self, gs):
        IzzetSpellementalsAPL.main_phase2(self, gs)
