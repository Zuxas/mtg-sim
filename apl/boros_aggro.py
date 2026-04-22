"""apl/boros_aggro.py -- Boros Aggro APL (Standard)
Cheap aggressive creatures + burn spells. Classic RDW+white splash.
Kill clock: T4-5 via Swiftspear/Adversary + burn.
"""
from apl.base_apl import BaseAPL
from apl.sb_mixin import SBPlanMixin
from engine.game_state import GameState

# Threats (sorted by cost / priority)
SWIFTSPEAR   = "Monastery Swiftspear"
PHOENIX      = "Phoenix Chick"
EPICURE      = "Voldaren Epicure"
ADVERSARY    = "Bloodthirsty Adversary"
SCOUNDREL    = "Charming Scoundrel"
KUMANO       = "Kumano Faces Kakkazan"
SQUEE        = "Squee, Dubious Monarch"
GODDRIC      = "Goddric, Cloaked Reveler"
FELDON       = "Feldon, Ronom Excavator"

# Burn / pump
PLAY_FIRE    = "Play with Fire"
LIGHTNING    = "Lightning Strike"
RAGE         = "Monstrous Rage"
FRENZY       = "Witchstalker Frenzy"

# Cheapest-first play priority
_PRIO_CREATURES = (SWIFTSPEAR, PHOENIX, EPICURE, KUMANO, SCOUNDREL,
                    ADVERSARY, SQUEE, FELDON, GODDRIC)
_PRIO_BURN = (PLAY_FIRE, LIGHTNING, RAGE, FRENZY)


class BorosAggroAPL(SBPlanMixin, BaseAPL):
    name = "Boros Aggro"
    win_condition_damage = 20
    max_turns = 12

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        creatures = sum(1 for c in hand if c.name in _PRIO_CREATURES)
        if lands == 0 or lands >= 6:
            return False
        if 2 <= lands <= 4 and creatures >= 2:
            return True
        return mulligans >= 2

    def bottom(self, hand, n):
        lands = [c for c in hand if c.is_land()]
        # Ship excess lands first
        return lands[2:][:n]

    def main_phase(self, gs: GameState):
        self._play_land_if_able(gs)
        # Drop cheapest creatures first to maximize pressure
        for name in _PRIO_CREATURES:
            for card in list(gs.hand()):
                if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    break
        # Burn to the face after threats are on board
        for name in _PRIO_BURN:
            for card in list(gs.hand()):
                if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    break
