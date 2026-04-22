"""apl/gruul_aggro.py -- Gruul Aggro APL (Standard)
Heartfire Hero + Monstrous Rage pump core. Slickshot Show-Off
reach, Emberheart Challenger for card advantage.
Kill clock: T4 via Hero + Rage combo, T5 reliably.
"""
from apl.base_apl import BaseAPL
from apl.sb_mixin import SBPlanMixin
from engine.game_state import GameState

# 1-drops
HEARTFIRE    = "Heartfire Hero"

# 2-drops
EMBERHEART   = "Emberheart Challenger"
MANIFOLD     = "Manifold Mouse"
SWIFTSPEAR   = "Monastery Swiftspear"
SLICKSHOT    = "Slickshot Show-Off"

# Pump / disruption
RAGE         = "Monstrous Rage"
SHOCK        = "Shock"
TALENT       = "Innkeeper's Talent"
SNAKESKIN    = "Snakeskin Veil"

# 3-drops
QUESTING     = "Questing Druid"

_PRIO_CREATURES = (HEARTFIRE, EMBERHEART, MANIFOLD, SWIFTSPEAR,
                    SLICKSHOT, QUESTING)
_PRIO_PUMP = (RAGE, SHOCK, SNAKESKIN, TALENT)


class GruulAggroAPL(SBPlanMixin, BaseAPL):
    name = "Gruul Aggro"
    win_condition_damage = 20
    max_turns = 10

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        creatures = sum(1 for c in hand if c.name in _PRIO_CREATURES)
        if lands == 0:
            return False
        # Aggro wants 2-3 lands + 2+ threats
        if 2 <= lands <= 4 and creatures >= 2:
            return True
        if lands == 1 and creatures >= 3:
            return True   # one-lander keep with critical mass
        return mulligans >= 2

    def bottom(self, hand, n):
        lands = [c for c in hand if c.is_land()]
        return lands[2:][:n]

    def main_phase(self, gs: GameState):
        self._play_land_if_able(gs)
        # Cheapest threats first — curve out
        for name in _PRIO_CREATURES:
            for card in list(gs.hand()):
                if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    break
        # Pump / reach after combat-relevant creatures are out
        for name in _PRIO_PUMP:
            for card in list(gs.hand()):
                if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    break
