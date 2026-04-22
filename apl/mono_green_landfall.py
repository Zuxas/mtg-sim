"""apl/mono_green_landfall.py -- Mono Green Landfall APL (Standard)
Ramp + landfall triggers via Fabled Passage / Escape Tunnel.
Pressure with Llanowar Elves on T1, Earthbender Ascension / Mightform
on board, fetch lands to trigger pumps.
Kill clock: T5-6 via landfall beats.
"""
from apl.base_apl import BaseAPL
from apl.sb_mixin import SBPlanMixin
from engine.game_state import GameState

# Ramp / early plays
LLANOWAR     = "Llanowar Elves"
ICETILL      = "Icetill Explorer"
BADGERMOLE   = "Badgermole Cub"

# Landfall payoffs
ASCENSION    = "Earthbender Ascension"
MIGHTFORM    = "Mightform Harmonizer"
MELTSTRIDER  = "Meltstrider's Resolve"
SAZH         = "Sazh's Chocobo"

# Utility / top-end
SAPLING      = "Sapling Nursery"
CHARM        = "Archdruid's Charm"

# Fetches / fixing
FABLED       = "Fabled Passage"
PROMISING    = "Promising Vein"
ESCAPE       = "Escape Tunnel"

_PRIO_RAMP = (LLANOWAR,)
_PRIO_CREATURES = (ICETILL, BADGERMOLE, MIGHTFORM, SAZH, MELTSTRIDER)
_PRIO_PAYOFFS = (ASCENSION, SAPLING, CHARM)


class MonoGreenLandfallAPL(SBPlanMixin, BaseAPL):
    name = "Mono Green Landfall"
    win_condition_damage = 20
    max_turns = 12

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        llanowar = sum(1 for c in hand if c.name == LLANOWAR)
        creatures = sum(1 for c in hand if c.name in _PRIO_CREATURES)
        if lands == 0 and llanowar == 0:
            return False
        if lands + llanowar >= 2 and creatures >= 1:
            return True
        return mulligans >= 2

    def bottom(self, hand, n):
        lands = [c for c in hand if c.is_land()]
        return lands[3:][:n]

    def main_phase(self, gs: GameState):
        self._play_land_if_able(gs)
        # Accelerate — T1 Llanowar is the whole plan
        for card in list(gs.hand()):
            if card.name == LLANOWAR and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                break
        # Landfall payoffs (drop early so later land plays count)
        for name in _PRIO_PAYOFFS:
            for card in list(gs.hand()):
                if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    break
        # Regular threats
        for name in _PRIO_CREATURES:
            for card in list(gs.hand()):
                if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    break
