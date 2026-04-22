"""apl/mono_red_aggro_standard.py -- Mono Red Aggro APL (Standard)
Pure red creature+burn deck. Hired Claw / Burnout Bashtronaut pressure,
Lightning Strike / Burst Lightning reach.
Kill clock: T4 via curve-out, T5 reliably.

Note: distinct from apl/mono_red_aggro.py which is Modern Burn.
Using the _standard suffix so the analyzer's format-specific
discovery picks it up cleanly.
"""
from apl.base_apl import BaseAPL
from apl.sb_mixin import SBPlanMixin
from engine.game_state import GameState

# 1-drops
HIRED_CLAW   = "Hired Claw"

# 2-drops
BURNOUT      = "Burnout Bashtronaut"
EMBERHEART   = "Emberheart Challenger"
RAZORKIN     = "Razorkin Needlehead"

# 3-drop
SCREAMING    = "Screaming Nemesis"

# Top-end
NOVA         = "Nova Hellkite"

# Burn / interaction
BURST        = "Burst Lightning"
LIGHTNING    = "Lightning Strike"
OBLITERATE   = "Obliterating Bolt"
SHOCK        = "Shock"
FRENZY       = "Witchstalker Frenzy"

_PRIO_CREATURES = (HIRED_CLAW, EMBERHEART, BURNOUT, RAZORKIN,
                    SCREAMING, NOVA)
_PRIO_BURN = (SHOCK, BURST, LIGHTNING, OBLITERATE, FRENZY)


class MonoRedAggroStandardAPL(SBPlanMixin, BaseAPL):
    name = "Mono Red Aggro"
    win_condition_damage = 20
    max_turns = 10

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        creatures = sum(1 for c in hand if c.name in _PRIO_CREATURES)
        burn = sum(1 for c in hand if c.name in _PRIO_BURN)
        if lands == 0 or lands >= 5:
            return False
        if 1 <= lands <= 3 and (creatures + burn >= 3):
            return True
        return mulligans >= 2

    def bottom(self, hand, n):
        lands = [c for c in hand if c.is_land()]
        return lands[2:][:n]

    def main_phase(self, gs: GameState):
        self._play_land_if_able(gs)
        # Creatures first, cheapest to most expensive
        for name in _PRIO_CREATURES:
            for card in list(gs.hand()):
                if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    break
        # Burn to the face
        for name in _PRIO_BURN:
            for card in list(gs.hand()):
                if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    break
