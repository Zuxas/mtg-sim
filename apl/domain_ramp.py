"""apl/domain_ramp.py -- Domain Ramp APL (Standard)
5-color ramp shell. Fix mana with Triomes, ramp on 3 via Briefcase /
Migration, drop Atraxa or Archangel on 5-7.
Kill clock: T6-7 via Atraxa beats or Archangel triple-mode.
"""
from apl.base_apl import BaseAPL
from apl.sb_mixin import SBPlanMixin
from engine.game_state import GameState

# Ramp + fixing
BRIEFCASE    = "Courier's Briefcase"
MIGRATION    = "Herd Migration"
INVASION     = "Invasion of Zendikar"

# Threats (cheapest to most expensive)
LEYLINE      = "Leyline Binding"
ARCHANGEL    = "Archangel of Wrath"
ATRAXA       = "Atraxa, Grand Unifier"

# Removal / interaction
DEPOPULATE   = "Depopulate"
THROAT       = "Go for the Throat"

# Value lands (cycle themselves)
BOSEIJU      = "Boseiju, Who Endures"
EIGANJO      = "Eiganjo, Seat of the Empire"

_PRIO_RAMP = (BRIEFCASE, MIGRATION, INVASION)
_PRIO_THREATS = (LEYLINE, ARCHANGEL, ATRAXA)
_PRIO_REMOVAL = (THROAT, DEPOPULATE)


class DomainRampAPL(SBPlanMixin, BaseAPL):
    name = "Domain Ramp"
    win_condition_damage = 20
    max_turns = 14

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        ramp = sum(1 for c in hand if c.name in _PRIO_RAMP)
        threats = sum(1 for c in hand if c.name in _PRIO_THREATS)
        # Ramp decks need 3+ lands to function
        if lands < 2:
            return False
        if 2 <= lands <= 5 and (ramp >= 1 or threats >= 1):
            return True
        return mulligans >= 2

    def bottom(self, hand, n):
        lands = [c for c in hand if c.is_land()]
        return lands[4:][:n]

    def main_phase(self, gs: GameState):
        self._play_land_if_able(gs)
        # Ramp first so the top-end lands on curve
        for name in _PRIO_RAMP:
            for card in list(gs.hand()):
                if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    break
        # Then threats in order of mana cost
        for name in _PRIO_THREATS:
            for card in list(gs.hand()):
                if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    break
        # Cheap interaction if mana left
        for name in _PRIO_REMOVAL:
            for card in list(gs.hand()):
                if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    break
