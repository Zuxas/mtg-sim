"""apl/uw_blink.py — UW Blink APL (Modern)
Phelia + Ephemerate + Guide of Souls engine. ETB value, blink to reset.
Kill clock: T4-5 via creature beats + Guide of Souls energy pump.
"""
from apl.base_apl import BaseAPL
from apl.sb_mixin import SBPlanMixin
from engine.game_state import GameState

PHELIA    = "Phelia, Exuberant Shepherd"
GUIDE     = "Guide of Souls"
OCELOT    = "Ocelot Pride"
ORCHID    = "White Orchid Phantom"
QUANTUM   = "Quantum Riddler"
STARFIELD = "Starfield Shepherd"
SOLITUDE  = "Solitude"
WITCH     = "Witch Enchanter"
EPHEMERATE= "Ephemerate"
PRISMATIC = "Prismatic Ending"
CONSIGN   = "Consign to Memory"

class UWBlinkAPL(SBPlanMixin, BaseAPL):
    name = "UW Blink"
    win_condition_damage = 20
    max_turns = 12

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4: return True
        lands   = sum(1 for c in hand if c.is_land())
        threats = sum(1 for c in hand if c.name in {PHELIA, GUIDE, OCELOT, ORCHID, QUANTUM})
        if lands == 0: return False
        if lands >= 2 and threats >= 1: return True
        return len(hand) <= 5 or mulligans >= 2

    def bottom(self, hand, n):
        lands = [c for c in hand if c.is_land()]
        return lands[3:][:n]

    def main_phase(self, gs: GameState):
        self._play_land_if_able(gs)
        for name in (GUIDE, PHELIA, OCELOT, ORCHID, QUANTUM, STARFIELD, WITCH, SOLITUDE):
            for card in list(gs.hand()):
                if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    break
        # Prismatic Ending / removal as interaction
        for card in list(gs.hand()):
            if card.name in {PRISMATIC} and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                break
